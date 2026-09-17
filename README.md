# discord-username-watcher

Polls Discord's username availability endpoint for a list of names and
fires an `@everyone` webhook alert when one frees up.

## Local

    pip install -r requirements.txt
    export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
    export USERNAMES="example,testname,cooluser"
    export DISCORD_AUTH_TOKEN=""      # optional, recommended
    python watcher.py

Health: http://localhost:8080/healthz

## Railway

1. Push to GitHub.
2. Railway → New Project → Deploy from GitHub repo.
3. Variables: DISCORD_WEBHOOK_URL, DISCORD_AUTH_TOKEN, USERNAMES.
4. Deploy.