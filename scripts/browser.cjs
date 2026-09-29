const fs = require('node:fs');
const {chromium} = require('playwright');

async function launchBrowser(extra = {}) {
  const options = {headless: true, ...extra};
  if (process.env.CHROME_PATH) {
    options.executablePath = process.env.CHROME_PATH;
  } else if (process.env.CHROME_CHANNEL && process.env.CHROME_CHANNEL !== 'chromium') {
    options.channel = process.env.CHROME_CHANNEL;
  } else if (!process.env.CHROME_CHANNEL && process.platform === 'darwin' &&
      fs.existsSync('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')) {
    options.channel = 'chrome';
  }
  try {
    return await chromium.launch(options);
  } catch (error) {
    throw new Error('ブラウザを起動できません。Chromeをインストールするか、npx playwright install chromium を実行し CHROME_CHANNEL=chromium を指定してください。\n' + error.message);
  }
}
module.exports = {launchBrowser};
