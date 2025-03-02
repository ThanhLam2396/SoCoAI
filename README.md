<h1 align="center">
  <br>
  <a href="https://socoai.xyz"><img src="https://github.com/ThanhLam2396/SoCoAI/blob/main/assets/favicon-socoai.png?raw=true" alt="SoCoAI" width="150"></a>
  <br>
  SoCoAI
  <br>
</h1>
<h4 align="center">A Powerful Suite of Tools Driven by AI.</h4>
<p align="center">
SoCoAI (Social + Community + AI) is more than just an AI Agent—it’s an intelligent automation solution designed to empower developers, communities, and businesses within blockchain ecosystems like Injective. By streamlining repetitive tasks such as news aggregation, market analysis, social media engagement, and community support, SoCoAI delivers a powerful, user-friendly, and adaptable tool. Whether it’s delivering real-time updates, tracking DApp trends, or assisting users via multi-platform chatbots, SoCoAI saves time, optimizes resources, and lets you focus on what truly matters—building and thriving in the fast-paced world of blockchain.
</p>


## 🚀 Features:
-   News Aggregation and Analysis: Collects news from X, filters valuable insights, generates concise recaps, and posts to X, Telegram, Discord, or saves to Google Sheets.
-   Market and On-Chain Analysis: Uses data from CoinGecko and Injective gRPC to assess trends and DApp performance.
-   Social Media Interaction: Auto-replies to comments and connects with KOLs to boost visibility.
-   Multi-Platform Chatbot: Supports users on Telegram, Discord, and website via a customizable terminal chatbot.
-   Visual Dashboard: Tracks social and on-chain data on the website.
-   CMS Customization: Easily adjusts chatbot settings without technical expertise.
    

##  🍀 Who Benefits?
-   Community Teams & News Trackers: SoCoAI helps them quickly gather and share ecosystem updates, even in local languages like Japanese or Spanish. It cuts workload with auto social chats and bots, freeing them for bigger tasks.
    
-   Builders & DApps: Developers use it to auto-answer user questions and explain their DApps, no manual work needed.
    
-   Project Founders & Layer-1s: They track DApps via data and social dashboards to plan ecosystem growth.
    
-   Individual Users: Crypto folks get news and charts to spot good DApps and invest smarter—fast info means less risk, more gain.
    
-   Non-Blockchain Businesses: Companies use its chat and social features to support customers and save costs.
    

## 📡 How It Works?

To see how SoCoAI manages tasks such as news summaries, market and on-chain analysis, and chatbot support, below is an illustration along with a detailed explanation of how it works:
![enter image description here](https://raw.githubusercontent.com/ThanhLam2396/images/4b14ceb4ada161c1ff224dcaaecc000ca26b8007/socoai-notransparent-light.svg)
#### Explanation:
**1. Data Collection**
The process starts by gathering data from multiple sources:
   - Social Media: Mainly from X (Twitter), which provides news, posts, and comments from crypto projects, dApps, and blockchain communities.
   -   Market Data: Retrieved through CoinGecko’s API, including key metrics such as MarketCap, trading Volume, total supply, current prices, All-Time High (ATH), percentage changes (daily, weekly, or monthly), inflation rates, and other market performance indicators.
   -   On-Chain Data: Sourced from Injective gRPC, injscan, and Cosmos platforms, including details like total supply, inflation rates, burned tokens, transaction volume, transaction speed (TPS - Transactions Per Second), staking amounts, staked asset value, active wallet count, smart contract activity, governance participation, block height, gas fees, and other blockchain performance metrics.
        
**2. Data Filtering**
   Raw data is filtered to remove unnecessary parts:
   -   Replies, quotes with no value, or content with sensitive keywords are discarded.
        
   -   Only reliable, ecosystem-relevant information is kept for further processing.
        
**3. Data Standardization (Transformation)**
    Filtered data is reorganized:
   -   Posts are structured consistently, edited for clarity, and credited with sources (author usernames) for transparency.
        
**4. Data Aggregation**  
    Standardized data is combined with pre-trained knowledge:
   -   This step merges new data with existing information and training to prepare for AI processing.
   -   Data is also stored in a database and storage system for future use.
        
**5. AI Processing** 
This is the core stage where SoCoAI turns transformed data into useful insights using Large Language Models (LLMs). The LLMs process natural language tasks—tokenizing, embedding, and analyzing context to extract meaning. Then, deep learning algorithms summarize content, analyze trends from quantitative data, and generate chatbot responses through inference.
    
**6. Output Based on Functions**  
   Depending on the need, SoCoAI produces results like:
   -   News recaps about dApps and ecosystems;
   -   Market trend analysis and dApp evaluations based on on-chain data;
   -   Responses to user comments and automated KOL interactions;     
   -   Smart chatbot replies based on user questions.  
        These outputs are shared on X, Telegram, and Discord for easy community access and stored in Google Sheets or databases for reporting and analysis later.
    

**🔗 Links**
-   X: https://x.com/SoCoAI – Follow automated blockchain and dApp news updates from social media posts.
    
-   Telegram: [https://t.me/injective_ecosystem_news](https://t.me/injective_ecosystem_news) – Get instant news, market analysis, and chat with the SoCoAI chatbot about ecosystems.
    
-   Discord: [https://discord.gg/wVQHC3W5](https://discord.gg/wVQHC3W5) – Get instant news, market analysis and interact directly with the SoCoAI chatbot for community support or blockchain updates.
    
-   Website: [https://socoai.xyz/](https://socoai.xyz/) – View a dashboard of social and on-chain data, get instant news, plus a chatbot terminal for quick info searches.
    
-   CMS: [https://cms.socoai.xyz/](https://cms.socoai.xyz/) – Customize the SoCoAI chatbot’s content and response style to your needs.
    
-   Documentation: [https://docs.socoai.xyz/](https://docs.socoai.xyz/) – Learn how to use SoCoAI with detailed guides on features and setup.
    

----------

## ⚡️ Quick Installation Guide

SoCoAI is engineered for seamless deployment via Docker Compose, enabling you to launch the full system in just a few steps. Follow this guide to install and run SoCoAI locally or on a server.

#### A. Requirements

-   Docker: Version 19.03 or higher ([Download Docker](https://docs.docker.com/get-docker/)).
    
-   Docker Compose: Version 1.27 or higher ([Download Docker Compose](https://docs.docker.com/compose/install/)).
    
-   Operating System: Linux, macOS, or Windows with WSL2.
    
-   Resources: Minimum 2GB RAM and 5GB free space.
    

#### B. Installation Steps

1.  Clone the Repository    
    ```bash
    git clone https://github.com/ThanhLam2396/socoai.git
    cd socoai
    ```
    
2.  Configure Environment
    -   Create config/setting.json from the sample config/setting.json.example:
        ```bash
        cp config/setting.json.example config/setting.json
        ```
        
    -   Edit config/setting.json with the necessary details:
        
        ```json
        {
            "BEARER_TOKEN": "xxxxxxx",                          # Twitter Bearer Token  
            "OPENAI_API_KEY": "sk-proj-xxxxx",                  # OpenAI API Key  
            "X_CONSUMER_KEY": "xxxxxxxxxxxxxxxxxxxx",           # Twitter Consumer Key  
            "X_CONSUMER_SECRET": "xxxxxxxxxxxxxxxxxxxxxxx",     # Twitter Consumer Secret  
            "X_ACCESS_TOKEN": "xxxxxxxxxxxxxxxxxx",             # Twitter Access Token  
            "X_ACCESS_TOKEN_SECRET": "xxxxxxxxxxxxxxxxxxxxxxxx",# Twitter Access Token Secret  
            "TELEGRAM_BOT_TOKEN": "xxxxxxxxxxxxxxxxxxxxxxxxxx", # Telegram Bot Token  
            "TELEGRAM_CHAT_ID": "@xxxxxxxxxxxxxxx",             # Telegram Chat ID  
            "DISCORD_BOT_TOKEN": "xxxxxxxxxxxxxxxx",            # Discord Bot Token  
            "DISCORD_CHANNEL_ID": "xxxxxxxxxxxxxxxxxxxxxxxxxx", # Discord Channel ID  
            "GOOGLE_SHEET_CREDENTIALS": "config/service-account.json", # Google Sheets Credentials  
            "SPREADSHEET_ID": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",     # Google Spreadsheet ID  
            "COINGECKO_API_KEY": "CG-xxxxxxxxxxxxxxxxxxxx",     # CoinGecko API Key  
            "LIST_IDS": ["1759xxxxxxxxx", "189466xxxxxx"],      # List of IDs  
            "LIST_USERS": ["user"],                             # List of Users  
            "TWEETS_FETCH_INTERVAL": 3600,                      # Twitter Fetch Interval (seconds)  
            "USERS_FETCH_INTERVAL": 3600,                       # Users Fetch Interval (seconds)  
            "TWITTER_REPLY_INTERVAL": 300,                      # Twitter Reply Interval (seconds)  
            "AUTO_COMMENT_INTERVAL": 300,                       # Auto Comment Interval (seconds)  
            "TOKEN_ID": "injective-protocol",                   # Token ID for Tracking  
            "TOKEN_ACCESS": "your-token"                        # Token Access Key  
        }
        ```
        
    -   Refer to the [Documentation](https://socoai.gitbook.io/socoai-docs/getting-started/markdown/setting.json) for detailed configuration.
        
3.  Run Docker Compose
    
    -   Start all SoCoAI services:
        ```bash
        docker-compose up -d --build
        ```
        ![enter image description here](https://github.com/ThanhLam2396/images/blob/main/docker-compose-up.gif?raw=true)
    -   This builds and runs: Redis (port 6379), fetch_user, telegram_bot, discord_bot, twitter_reply, auto_comment, update_news, daily_recap, market_news, onchain_news, dapps_tracker, and web_app (port 5555).
        
4.  Check Status
    
    -   View running containers:
		        ```bash
		        docker ps
		        ```
        ![enter image description here](https://github.com/ThanhLam2396/images/blob/main/docker%20ps.gif?raw=true)
    -   Access the website at: http://localhost:5555.
        
5.  Stop the System (if needed)

	-   Stop docker compose:
					 ```bash
      docker-compose down
		    ```
     ![enter image description here](https://github.com/ThanhLam2396/images/blob/main/docker-compose-down.gif?raw=true)

## 📒 Notes

-   Ensure config/setting.json is correctly configured before starting.
    
-   Data is stored in ./storage; adjust volumes as needed.
    
-   Visit [https://docs.socoai.xyz/](https://docs.socoai.xyz/) for additional guidance.