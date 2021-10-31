 # Sniper-WSB
 
 Kudos to **Lautaro-L** for the code base. The code is almost entirely his. Repository [here](https://github.com/Lautaro-L/Binance_New_Coins_Scraper).
 
 ## Configuration

 1. Set Binance API key & secret in ```template_auth.yml``` and rename it to ```auth.yml```
 2. Set Telegram key & chat id of a bot you created in ```template_telegram.yml``` and rename it to ```telegram.yml```
 3. Check wether all parameters in ```template_config.yml``` satisfy you. Disable testmode when you're ready and rename to ```config.yml```

 ## Installation
 
 ```$ sudo apt install telegram-cli```
 ```$ pip3 install -r requirements.txt```
 
 ## Usage
 
 ```$ bash entrypoint.sh```
 
 ### Daemonization
 
 You may want to run this sniper as a daemon. To achieve that, you can create a daemon running in the userspace as follows:
 
 ```$ mkdir -p ~/.config/systemd/user```
 ```$ touch bot.service```
 Set ```bot.service``` content to:
 ```
 [Unit]
 Description=bot

 [Service]
 WorkingDirectory=/path/to/repo/
 ExecStart=/bin/bash /path/to/repo/bootstrapper.sh
 # Restart=on-failure

 [Install]
 WantedBy=multi-user.target
```
 Run the daemon:
 ```$ systemctl --user daemon-reload```
 ```$ systemctl --user enable bot.service```
 ```$ systemctl --user start bot.service```
 
 ## Disclaimer

 The software is provided "AS IS" and can result in financial loss. I don't take any responsibility. Contributions are welcome.
