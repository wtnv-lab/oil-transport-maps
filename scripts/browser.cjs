/**
 * PNG出力と背景取得で共通のブラウザー選択。
 * CHROME_PATH > CHROME_CHANNEL > macOSのChrome > PlaywrightのChromiumの順。
 * CHROME_CHANNEL=chromium は、macOSのChrome自動検出を使わない指定。
 */
const fs = require('node:fs');
const {chromium} = require('playwright');

async function launchBrowser(extra = {}) {
  const options = {headless: true, ...extra};
  const macChrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

  if (process.env.CHROME_PATH) {
    options.executablePath = process.env.CHROME_PATH;
  } else if (process.env.CHROME_CHANNEL && process.env.CHROME_CHANNEL !== 'chromium') {
    options.channel = process.env.CHROME_CHANNEL;
  } else if (
    !process.env.CHROME_CHANNEL &&
    process.platform === 'darwin' &&
    fs.existsSync(macChrome)
  ) {
    options.channel = 'chrome';
  }

  try {
    return await chromium.launch(options);
  } catch (error) {
    throw new Error(
      'ブラウザを起動できません。Chromeをインストールするか、' +
      'npx playwright install chromium を実行し ' +
      'CHROME_CHANNEL=chromium を指定してください。\n' + error.message
    );
  }
}

module.exports = {launchBrowser};
