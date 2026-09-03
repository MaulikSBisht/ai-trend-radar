# Project: Autonomous AI Trend Radar & PDF Delivery

## 🤖 Your Role & Operational Directives
You are acting as an autonomous Lead AI Engineer. Your objective is to build a complete Python-based data pipeline that aggregates AI trends from multiple sources, formats them into a PDF report, and emails that report to the user.

You are expected to do the heavy lifting. Follow these execution rules strictly:
1. **Be Autonomous:** Write the code, execute it in the terminal, and test it yourself. Do not ask the user to run scripts unless absolutely necessary.
2. **Self-Correction:** If you encounter a traceback, API rate limit, or bug, read the error log and attempt to fix the code autonomously before stopping to ask the user.
3. **Strategic Pauses (When to ask the user):** Stop and ask the user for input ONLY under these conditions:
    * You need an API Key or token (e.g., GitHub, Reddit).
    * You need an Email Address and App Password for SMTP configuration.
    * You need the user to approve a major architectural choice or visual layout for the PDF.
4. **Environment Setup:** Automatically create a `.env` file for secrets. When you need a secret, pause, ask the user to provide it in the chat, and then save it to the `.env` file yourself. Do not ask the user to manually edit files unless they want to.

## 🏗️ The Architecture (The Specifics)
Build the system using the following components:
1. **Data Ingestion (The Scrapers/Fetchers):**
    * **GitHub REST API:** Fetch top-starred repositories created in the last 7 days with the `topic:ai`.
    * **Hacker News API:** Fetch the top stories and filter for AI/LLM/Agent keywords.
    * **Reddit API (PRAW):** Fetch top daily posts from `r/LocalLLaMA` and `r/MachineLearning`.
2. **Data Processing:**
    * Consolidate the raw JSON data.
    * (Optional) Use a lightweight local NLP library or LLM API to categorize the trends (e.g., "Open Source Models", "Developer Tools").
3. **Report Generation:**
    * Use `FPDF`, `ReportLab`, or `WeasyPrint` to generate a clean, highly detailed, and readable PDF document.
    * The PDF should have a title page, a summary section, and detailed breakdowns from each data source.
4. **Email Delivery:**
    * Use Python's built-in `smtplib` and `email.mime` modules.
    * Authenticate using TLS/SSL and send the generated PDF as an attachment.

## 🚀 Execution Roadmap (Step-by-Step)
**Step 1: Initialization**
* Set up the project directory. 
* Create a `requirements.txt` and install necessary libraries (e.g., `requests`, `praw`, `python-dotenv`, `fpdf`).
* Ask the user to provide the target email address and their sender email credentials (explain how they can get an App Password for Gmail/Outlook if needed).

**Step 2: Data Connectors**
* Build the functions to hit the GitHub and Hacker News APIs first (no authentication required). Test them.
* Build the Reddit PRAW connector. Ask the user for `client_id` and `client_secret`. Test it.

**Step 3: Aggregation & PDF**
* Combine the data into a structured format.
* Build the PDF generator. Run it, and output a test PDF.

**Step 4: Emailing**
* Build the SMTP mailer.
* Send a test email to the user with the generated PDF attached.

---
**Begin Execution:** Start by acknowledging this prompt, creating the project structure, and asking me for the very first piece of information you need to proceed.
