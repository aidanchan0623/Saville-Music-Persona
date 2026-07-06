# YouTube Music authentication setup

Saville Music Persona uses `ytmusicapi` locally. The preferred authentication route is OAuth, and all credential files stay on your laptop.

## What you need

- Python dependencies installed with `scripts/setup_windows.ps1`
- A Google account with access to your YouTube Music account
- A Google Cloud project where the YouTube Data API is enabled
- A local OAuth client ID and client secret

As of current `ytmusicapi` documentation, OAuth requires a Client ID and Client Secret for the YouTube Data API. Create an OAuth client ID and choose **TVs and Limited Input devices**.

## Create `oauth.json`

Run these commands from the repository root in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
New-Item -ItemType Directory -Force .\backend\private
Set-Location .\backend\private
..\.venv\Scripts\ytmusicapi.exe oauth
```

If the last command path does not resolve, use:

```powershell
..\.venv\Scripts\python.exe -m ytmusicapi oauth
```

The OAuth flow prints a device-code login URL. Complete it in your browser. It writes:

```text
backend/private/oauth.json
```

## Configure client ID and secret

Set these for your local shell or put them in a private, ignored environment file that you load yourself:

```powershell
$env:YTMUSIC_OAUTH_CLIENT_ID="your-client-id"
$env:YTMUSIC_OAUTH_CLIENT_SECRET="your-client-secret"
$env:YTMUSIC_AUTH_FILE="backend/private/oauth.json"
```

Then start the app:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_dev.ps1
```

Open `http://localhost:5173`, go to **Settings**, and use **Recheck Connection**.

## Security rules

- Do not commit `backend/private/`.
- Do not commit `oauth.json`, browser headers, cookies, `.env`, raw listening history, or database files.
- Do not automate browser cookie extraction.
- Browser-header authentication should only be used as a manual advanced fallback. Treat the header file as sensitive account-access data.

## Advanced fallback: manual browser headers

If OAuth succeeds but YouTube Music returns `HTTP 400: Request contains an invalid argument`, use manual browser-header auth. This is a known ytmusicapi/OAuth failure mode caused by YouTube-side changes. Browser headers are sensitive because they include account-access cookies.

1. Open `https://music.youtube.com` in the browser where you are signed in.
2. Press `F12` to open Developer Tools.
3. Open the **Network** tab.
4. Click around YouTube Music, for example **Library**.
5. In the Network list, select a request to `music.youtube.com/youtubei/v1/browse` or another `youtubei/v1/...` request.
6. Right-click the request and choose **Copy** -> **Copy request headers**.
7. In PowerShell from the repository root, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\create_browser_auth.ps1
```

8. Paste the copied request headers into the terminal.
9. Press `Ctrl+Z`, then `Enter`.

The script writes:

```text
backend/private/browser.json
```

Restart the app and use **Settings** -> **Recheck Connection**.

## Troubleshooting

- If the app says `oauth.json` is missing, confirm it is at `backend/private/oauth.json`.
- If the app says OAuth client values are missing, set `YTMUSIC_OAUTH_CLIENT_ID` and `YTMUSIC_OAUTH_CLIENT_SECRET` before starting the backend.
- If Google rejects the OAuth client type, confirm the client is for **TVs and Limited Input devices**.
- If history is sparse or undated, YouTube Music may not expose a full year of parseable play history through `ytmusicapi`.
