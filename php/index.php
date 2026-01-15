<?php
/**
 * Travel Concierge Agent - DreamHost Landing Page
 *
 * This page redirects to your Streamlit app hosted on Streamlit Community Cloud.
 *
 * SETUP:
 * 1. Push your code to GitHub
 * 2. Go to https://share.streamlit.io
 * 3. Connect your GitHub repo
 * 4. Deploy the app
 * 5. Update STREAMLIT_APP_URL below with your app URL
 */

// UPDATE THIS with your Streamlit Community Cloud URL
$STREAMLIT_APP_URL = 'https://your-app-name.streamlit.app';

// Set to true to embed in iframe, false to redirect
$USE_IFRAME = true;

// Check if app URL is configured
$isConfigured = ($STREAMLIT_APP_URL !== 'https://your-app-name.streamlit.app');
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Travel Concierge Agent</title>
    <?php if ($isConfigured && !$USE_IFRAME): ?>
    <meta http-equiv="refresh" content="0;url=<?php echo htmlspecialchars($STREAMLIT_APP_URL); ?>">
    <?php endif; ?>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }

        .container {
            width: 100%;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .header {
            background: rgba(0, 0, 0, 0.2);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            font-size: 1.3rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .header a {
            color: white;
            text-decoration: none;
            opacity: 0.8;
            font-size: 0.9rem;
        }

        .header a:hover {
            opacity: 1;
        }

        .app-frame {
            flex: 1;
            border: none;
            width: 100%;
            background: white;
        }

        .setup-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 40px;
            color: white;
        }

        .setup-card {
            background: white;
            border-radius: 16px;
            padding: 40px;
            max-width: 600px;
            color: #333;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }

        .setup-card h2 {
            margin-bottom: 20px;
            color: #262730;
        }

        .setup-card p {
            color: #666;
            margin-bottom: 20px;
            line-height: 1.6;
        }

        .steps {
            text-align: left;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }

        .steps ol {
            margin-left: 20px;
        }

        .steps li {
            margin-bottom: 12px;
            color: #444;
        }

        .steps code {
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
        }

        .steps a {
            color: #667eea;
        }

        .btn {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 14px 28px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            margin-top: 10px;
        }

        .btn:hover {
            background: #5a6fd6;
        }
    </style>
</head>
<body>
    <div class="container">
        <?php if ($isConfigured): ?>
            <div class="header">
                <h1>✈️ Travel Concierge Agent</h1>
                <a href="<?php echo htmlspecialchars($STREAMLIT_APP_URL); ?>" target="_blank">Open in new tab ↗</a>
            </div>
            <?php if ($USE_IFRAME): ?>
                <iframe src="<?php echo htmlspecialchars($STREAMLIT_APP_URL); ?>?embedded=true" class="app-frame" allow="clipboard-write"></iframe>
            <?php endif; ?>
        <?php else: ?>
            <div class="setup-container">
                <div class="setup-card">
                    <h2>🚀 Setup Required</h2>
                    <p>Your Travel Concierge Agent needs to be deployed to Streamlit Community Cloud (it's free!).</p>

                    <div class="steps">
                        <ol>
                            <li>Push your code to <a href="https://github.com" target="_blank">GitHub</a></li>
                            <li>Go to <a href="https://share.streamlit.io" target="_blank">share.streamlit.io</a></li>
                            <li>Click <strong>"New app"</strong> and connect your repo</li>
                            <li>Set the main file to <code>app.py</code></li>
                            <li>Add your secrets (API keys) in the app settings</li>
                            <li>Copy your app URL (e.g., <code>https://your-app.streamlit.app</code>)</li>
                            <li>Edit this file and update <code>$STREAMLIT_APP_URL</code></li>
                        </ol>
                    </div>

                    <a href="https://share.streamlit.io" target="_blank" class="btn">Deploy on Streamlit Cloud →</a>
                </div>
            </div>
        <?php endif; ?>
    </div>
</body>
</html>
