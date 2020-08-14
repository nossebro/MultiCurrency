# MultiCurrency

Add more currencies with (Streamlabs-like) commands and listening for events to add or remove currency. Works like the normal currency command, eg:

`!<currencyname> add|remove <user>|+viewers|+active <amount>`

`!<currencyname> transfer <from-user> <to-user>`

## Installation

1. Install the script in SLCB. (Please make sure you have configured the correct [32-bit Python 2.7.13](https://www.python.org/ftp/python/2.7.13/python-2.7.13.msi) Lib-directory).
2. Insert the API_Key.js by right-click the script in SLCB.
3. Reload all scripts, so the new API_Key.js file gets picked up.
4. Create a `Config.ini` in the script folder:

Example Config.ini:

```INI
[Second Points]
Command = points2
Cooldown = 1
Database = points2.db

[Third Points]
Command = points3
Cooldown = 1
Database = points3.db

[Rewards]
00000000-0000-0000-0000-000000000000 = !points2 add {user} 1000
00000000-0000-0000-0000-000000000000 = !points3 add {user} 1
00000000-0000-0000-0000-000000000000 = !points2 add +viewers 1000

[Defaults]
AddToUser = {broadcaster} --> Successfully given {user} {amount} {currency}
RemoveFromUser = {broadcaster} --> Successfully removed {amount} {currency} from {user}
AddToViewers = {broadcaster} --> {action} giving {amount} {currency} to {group} in chat
RemoveFromViewers = {broadcaster} --> {action} removing {amount} {currency} to {group} in chat
Response = {user}: {amount} {currency}
```
