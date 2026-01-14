# 5. Vercel Serverless Entry Point
async def handler(request):
    # Handle Telegram's POST request
    if request.method == "POST":
        if not app.running:
            await app.initialize()
        try:
            data = await request.json()
            update = Update.de_json(data, app.bot)
            await app.process_update(update)
            return {"statusCode": 200, "body": "Success"}
        except Exception as e:
            print(f"Error: {e}")
            return {"statusCode": 500, "body": str(e)}

    # Handle Browser GET request (Prevents 405 error)
    elif request.method == "GET":
        return {
            "statusCode": 200, 
            "headers": {"Content-Type": "text/html"},
            "body": "<h1>Baobei Bot is Online ✅</h1><p>Telegram Webhook is active.</p>"
        }

    return {"statusCode": 405, "body": "Method Not Allowed"}
    # --- Bottom of your index.py ---

async def handler(request):
    # Handle Telegram messages (POST)
    if request.method == "POST":
        if not app.running:
            await app.initialize()
        try:
            data = await request.json()
            update = Update.de_json(data, app.bot)
            await app.process_update(update)
            return {"statusCode": 200, "body": "OK"}
        except Exception as e:
            return {"statusCode": 500, "body": str(e)}

    # Handle browser visits (GET) - This stops the downloading!
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html"},
        "body": "<h1>Bot is Online ✅</h1>"
    }
