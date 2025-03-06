import requests
from bs4 import BeautifulSoup
import discord
import os
from dotenv import load_dotenv
import signal
import asyncio  

# Load environment variables from .env file
load_dotenv()

# Get Discord token and channel ID from environment variables, cant be pushed to github
# DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
# CHANNEL_ID = int(os.getenv("YOUR_DISCORD_CHANNEL_ID"))

# Set up Discord intents (message content is required for reading user messages)
intents = discord.Intents.default()
intents.message_content = True  

# Initialize Discord client with intents
client = discord.Client(intents=intents)

# Function to scrape job details from a given URL
def scrape_job_post(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"❌ Failed to retrieve page (Status Code: {response.status_code})")
        return None, None, None, None, None  # Return None values if request fails

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract job title
    title_element = soup.find("h1", class_="text--break-word")
    job_title = title_element.text.strip() if title_element else "Title not found"

    # Extract company name and location
    company_name = "Company not found"
    location = "Location not found"
    company_info = soup.find("p", class_="header__info")
    
    if company_info:
        company_span = company_info.find("a").find("span")  
        if company_span:
            company_name = company_span.text.strip()

        location_span = company_info.find_all("a")[-1].find("span")
        if location_span:
            location = location_span.text.strip()

    # Extract deadline information
    deadline = "Deadline not found"
    deadline_info = soup.find_all("p", class_="header__info")
    
    # Checking if it's the last day to apply
    warning_span = soup.find("span", class_="header__info--warning")
    if warning_span and "Last day to apply" in warning_span.text:
        deadline = "Application ends today"
    
    if len(deadline_info) > 1:
        deadline_span = deadline_info[1].find_all("span")
        if len(deadline_span) > 1:
            end_text = deadline_span[1].text.strip()
            if "Ends" in end_text:
                deadline = "Ends " + end_text.split("Ends")[-1]
            elif "Päättyy" in end_text:
                deadline = "Ends " + end_text.split("Päättyy")[-1]
            elif "days remaining" in end_text:
                deadline = end_text
            elif "päivää jäljellä" in end_text:
                days_remaining = end_text.split("päivää jäljellä")[0].strip()
                deadline = f"{days_remaining} päivää jäljellä"
            elif "Open until further notice" in end_text:
                deadline = "Open until further notice"
            elif "Published" in end_text:
                deadline = "Published " + end_text.split("Published")[-1].strip()

    # Extract and truncate job description to 200 characters
    description = "Description not found"
    description_element = soup.find("div", class_="gtm-apply-clicks description description--jobentry")
    if description_element:
        description_text = description_element.text.strip()
        description = description_text[:200] + "…" if len(description_text) > 200 else description_text  

    return job_title, company_name, location, deadline, description

# Function to send job details as a message in Discord
async def send_message_to_discord(job_title, company_name, location, deadline, description, url, channel):
    embed = discord.Embed(
        title="✅ Job Post Found!", 
        description=f"🏢 **Company:** {company_name}\n"
                    f"💼 **Job Title:** {job_title}\n"
                    f"📍 **Location:** {location}\n"
                    f"📅 **Deadline:** {deadline}\n"
                    f"📜 **Description:** {description}\n"
                    f"🔗 **More Info:** [Click Here]({url})",
        color=discord.Color.green()  
    )

    await channel.send(embed=embed)

# Event: when the bot is ready
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    print("✅ Bot is ready! Send a job post URL using '!job <URL>'.")

    # Keep waiting for messages
    while True:
        print("🔄 Waiting for input...")  # Debugging message
        
        # Wait for a user message that starts with "!job"
        message = await client.wait_for("message", check=lambda message: message.author != client.user)
        
        print(f"✅ Received message: {message.content}")  # Debugging

        if message.content.startswith("!job "):
            job_url = message.content[5:].strip()  # Extract URL from message
            
            print(f"✅ Job URL received: {job_url}")  # Debugging
            
            if job_url.startswith("http"):
                job_title, company_name, location, deadline, description = scrape_job_post(job_url)

                if job_title and company_name and location and deadline:
                    print(f"✅ Job Post Found!\n"
                          f"🏢 Company: {company_name}\n"
                          f"💼 Job Title: {job_title}\n"
                          f"📍 Location: {location}\n"
                          f"📅 Deadline: {deadline}\n"
                          f"📜 Description: {description}\n"
                          f"🔗 URL: {job_url}")

                    # Get the channel and send the job post
                    channel = client.get_channel(CHANNEL_ID)
                    if channel:
                        await send_message_to_discord(job_title, company_name, location, deadline, description, job_url, channel)
                    
                    # Delete the user's original message containing the job URL
                    await message.delete()  
                else:
                    print("❌ Failed to scrape job post. Please check the URL and try again.")
            else:
                print("⚠️ Please provide a valid job post URL.")

# Handle graceful shutdown on interrupt signal (Ctrl+C)
def signal_handler(sig, frame):
    print("Bot is shutting down due to signal.")
    client.loop.stop()

signal.signal(signal.SIGINT, signal_handler)

# Start the bot
# client.run(DISCORD_TOKEN)
