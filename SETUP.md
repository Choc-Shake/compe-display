# CompE Snack Bar Display: setup guide

No coding needed. Takes about 20 minutes the first time.

## 1. Install it on the club PC

Open **Terminal** on the club computer (Ubuntu), paste this line, and press Enter:

```bash
curl -fsSL https://raw.githubusercontent.com/Choc-Shake/compe-display/main/install.sh | bash
```

It will ask for your password, then walk you through setup:
- **Robot key:** if the robot's `.json` file is in your Downloads folder it finds it for you; otherwise drag the file into the Terminal window.
- **Snack sheet:** paste the spreadsheet's link straight from your browser.
- **Calendar:** paste the club calendar's secret iCal address.

At the end it tests the spreadsheet and tells you in plain words what's wrong if it can't connect (for example, if the sheet hasn't been shared with the robot yet).

Press Enter to skip anything; that part shows sample data until you fill it in.

**Change settings later:** run `~/compe-display/setup` in Terminal.

To update the display later, run the same install line again.

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

Then run `~/compe-display/setup` and paste the sheet link when it asks.

> Only the Item, Sell Price, Stock, Low Stock At and Units Sold columns are read. Cost, profit and exec-taken never appear on screen.

## 3. Connect the club calendar

In Google Calendar, open the club calendar's **⋮ → Settings and sharing** and copy **Secret address in iCal format**. Paste it when setup asks.

## Handy things

| Want to… | Do this |
|---|---|
| Exit the full-screen display | Press **Alt+F4** |
| Bring it back | Log out and log back in, or restart the PC |
| Rotate the screen | **Settings → Displays → Orientation → Portrait** |
| Test the confetti | Press **S** on the keyboard while the display is showing |
| See what's wrong | `journalctl --user -u compe-display -n 50` |
| Change fun facts | Edit the `ticker:` list near the top of the script in `static/index.html` |
