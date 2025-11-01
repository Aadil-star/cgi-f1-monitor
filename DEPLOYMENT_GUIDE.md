# Deployment guide - Render + Mailjet
1. Create accounts
   - Mailjet: https://www.mailjet.com - sign up, verify your sender email, and generate API keys.
   - Render: https://render.com - sign up and verify your account.
2. Prepare repository
   - Add these files: main.py, requirements.txt, render.yaml, .env.example.
   - Push to GitHub.
3. Configure Render
   - New -> Cron Job -> Connect repository.
   - Command: python main.py
   - Schedule: 0,30 * * * * (every 30 minutes)
4. Add Environment Variables
   - MJ_APIKEY_PUBLIC, MJ_APIKEY_PRIVATE, RECIPIENT_EMAIL, FROM_EMAIL, CONSULATE_URLS
5. Deploy & check logs.
