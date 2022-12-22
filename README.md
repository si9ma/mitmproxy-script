# mitmproxy-script
use mitmproxy with javascript support(like surge/Quantumult X, etc.)

## 实现HBO等流媒体平台字幕翻译

### 原理
通过[mitmproxy](https://mitmproxy.org/) 以及 [流媒体平台字幕增强及双语模块](https://github.com/DualSubs/DualSubs)提供的js脚本来实现HBO等流媒体平台字母的翻译, mitmproxy提供了https的解密能力，所以可以用mitmproxy来通过中间人攻击改写所有字幕请求的改写（在字幕列表中强插一个中文字幕选项，将英文字幕通过google等进行翻译成中文）

### 使用方法

1. 安装mitmproxy
2. 安装NodeJS
3. 在设备(iphone、mac、Apple TV等)上安装mitmproxy证书，并信任
4. 通过如下命令启动mitmproxy

```bash
mitmdump -s ./mitmproxy-script.py --allow-hosts 'mitmproxy' --allow-hosts 'manifests(\.v2)?\.api\.hbo\.com' --set connection_strategy=lazy
```
5. 在设备上设置代理(wifi代理或者http全局代理)，代理地址为mitmproxy所在的ip地址，端口为8080
6. 打开HBO等流媒体平台，播放视频，选择中文字幕，即可看到中英双语字幕