# DreamHost Deployment Guide

Since DreamHost Shared Hosting can't run Python apps directly, we'll host the app on **Streamlit Community Cloud (FREE)** and embed it on your DreamHost site.

## Step 1: Push Code to GitHub

1. Create a GitHub repository
2. Push your Travel Concierge Agent code to it
3. Make sure these files are included:
   - `app.py`
   - `requirements.txt`
   - `.streamlit/config.toml`
   - All other `.py` files

**Do NOT push:**
- `.env` (contains your API keys)
- `data/` folder
- `venv/` folder

## Step 2: Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click **"New app"**
4. Select your repository
5. Set main file path: `app.py`
6. Click **"Deploy"**

## Step 3: Add Your Secrets

In Streamlit Cloud:

1. Click the **⋮** menu on your app
2. Select **"Settings"**
3. Go to **"Secrets"**
4. Add your API keys:

```toml
OPENAI_API_KEY = "sk-your-key-here"
AMADEUS_API_KEY = "your-amadeus-key"
AMADEUS_API_SECRET = "your-amadeus-secret"
```

5. Click **"Save"**

## Step 4: Upload PHP to DreamHost

1. Upload the `php/` folder to your DreamHost site
2. Edit `index.php` and update line 16:

```php
$STREAMLIT_APP_URL = 'https://your-app-name.streamlit.app';
```

Replace with your actual Streamlit Cloud URL.

## Step 5: Access Your App

- **Direct URL:** `https://your-app-name.streamlit.app`
- **Via DreamHost:** `https://yourdomain.com/php/`

## Files in This Folder

| File | Purpose |
|------|---------|
| `index.php` | Embeds your Streamlit app in an iframe |
| `.htaccess` | Security settings for Apache |
| `README.md` | This guide |

## Troubleshooting

### App shows "Setup Required"
- Edit `index.php` and set the correct `$STREAMLIT_APP_URL`

### App won't load in iframe
- Some browsers block iframes; users can click "Open in new tab"
- Set `$USE_IFRAME = false` to redirect instead

### API errors in the app
- Check your secrets are set correctly in Streamlit Cloud
- Go to app Settings → Secrets

## Cost

- **Streamlit Community Cloud:** FREE
- **DreamHost Shared Hosting:** Your existing plan

## Limitations

- App may "sleep" after inactivity on free tier (wakes up when visited)
- User data is stored on Streamlit's servers, not DreamHost
