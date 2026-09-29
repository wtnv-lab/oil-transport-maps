const {spawnSync} = require('node:child_process');
const path = require('node:path');
const names = ['middle-east','global'];
const choice = process.argv[2] || 'all';
if (process.argv.length > 3 || (choice !== 'all' && !names.includes(choice))) {
  console.error('Usage: npm run refresh-basemap -- all|middle-east|global');
  process.exit(2);
}
for (const name of choice === 'all' ? names : [choice]) {
  console.log(`背景地図を更新します（ネット接続が必要）: ${name}`);
  const result=spawnSync(process.execPath,[path.join(__dirname,'../maps',name,'render-base.cjs')],{stdio:'inherit'});
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
}
console.log('背景更新完了。./build.sh all で完成地図を再作図してください。');
