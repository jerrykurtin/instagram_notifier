# instagram_notifier
checks to see if there's any life events from my friends on instagram


## Setup

### 1. Install dependencies

CR jkurtin: put the conda env here

### 2. Configure credentials

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

## Environment variables

All credentials are loaded from a `.env` file in the working directory.

| Variable | Description |
|---|---|
| `NOTIFY_EMAIL` | Gmail address to send from and to |
| `NOTIFY_APP_PASSWORD` | Gmail App Password (see below) |
| `ANTHROPIC_API_KEY` | Anthropic API key (see below) |

### Generating a Gmail App Password

Gmail requires an App Password rather than your regular account password when authenticating via SMTP. App Passwords are only available if your account has 2-Step Verification enabled.

1. Go to your [Google Account](https://myaccount.google.com) and sign in.
2. Navigate to **Security** → **2-Step Verification** and enable it if not already on.
3. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
4. Under "App name", enter something descriptive like `instagram-notifier` and click **Create**.
5. Google will display a 16-character password. Copy it immediately — it won't be shown again.
6. Paste it as the value of `NOTIFY_APP_PASSWORD` in your `.env` file. The spaces in the password are optional; both `xxxx xxxx xxxx xxxx` and `xxxxxxxxxxxxxxxx` work.

### Generating an Anthropic API key

1. Go to [console.anthropic.com](https://console.anthropic.com) and sign in or create an account.
2. Navigate to **API Keys** in the left sidebar.
3. Click **Create Key**, give it a name, and click **Create**.
4. Copy the key immediately — it is only shown once.
5. Paste it as the value of `ANTHROPIC_API_KEY` in your `.env` file.


## Run

CR jkurtin: Add run instructions
