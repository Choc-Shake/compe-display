# CompE Snack Bar Display: setup guide

No coding needed. Takes about 20 minutes the first time.

## 1. Install it on the club PC

Open **Terminal** on the club computer (Ubuntu), paste this line, and press Enter:

```bash
curl -fsSL https://raw.githubusercontent.com/Choc-Shake/compe-display/main/install.sh | bash
```

It will ask for your password, then three questions. You can press Enter to skip any of them and fill them in later. Skipped items show sample data.

To update the display later, run the same line again.

## 2. Let the display read the snack sheet

The display uses its own Google "robot" account that can **only read** the sheet. It can never change anything.

**Make the robot (once):**
1. Go to <https://console.cloud.google.com/> and sign in with a club Google account.
2. Create a project called `compe-display`.
3. Search for **Google Sheets API** and click **Enable**. Do the same for **Google Drive API**.
4. Go to **IAM & Admin → Service Accounts → Create service account**. Name it `snack-display` and click **Done**.
5. Click the new account, open **Keys → Add key → Create new key → JSON**. A file downloads.
6. Rename that file to `robot-key.json` and put it in the `compe-display` folder in your home folder.

**Share the sheet with the robot:**
1. Copy the robot's email address. It looks like `snack-display@compe-display.iam.gserviceaccount.com`.
2. Ask whoever owns the snack spreadsheet to click **Share**, paste that email in, set it to **Viewer**, and uncheck "Notify".

**Tell the display which sheet:** the sheet ID is the long code in its web address:
`docs.google.com/spreadsheets/d/`**`THIS-LONG-CODE`**`/edit`
Put it in `~/compe-display/config.toml` next to `id =` if you skipped it during install.

> Only the Item, Sell Price, Stock, Low Stock At and Units Sold columns are read. Cost, profit and exec-taken never appear on screen.

## 3. Connect the club calendar

1. Open Google Calendar, then go to the club calendar's **⋮ → Settings and sharing**.
2. Scroll to **Secret address in iCal format** and copy it.
3. Paste it into `config.toml` next to `ical_url =`.

## 4. Apply changes

After editing `config.toml`, restart the display server with this command in Terminal:

```bash
systemctl --user restart compe-display
```

## Handy things

| Want to… | Do this |
|---|---|
| Exit the full-screen display | Press **Alt+F4** |
| Bring it back | Log out and log back in, or restart the PC |
| Rotate the screen | **Settings → Displays → Orientation → Portrait** |
| Test the confetti | Press **S** on the keyboard while the display is showing |
| See what's wrong | `journalctl --user -u compe-display -n 50` |
| Change fun facts | Edit the `ticker:` list near the top of the script in `static/index.html` |
