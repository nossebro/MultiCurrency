# MultiCurrency

Add more currencies with (Streamlabs-like) commands and listening for events to add or remove currency. Works like the normal currency command, eg:

`!<currencyname> add|remove <user>|+viewers|+active <amount>`

`!<currencyname> transfer <from-user> <to-user>`

For the possibility to redeem currency with Twitch Channel Points, [TwitchPubSubMirror](https://github.com/nossebro/TwitchPubSubMirror) must be installed, and the subscription of Twitch Channel Points Rewards must be enabled in its settings.

## Installation

1. Install the script in SLCB. (Please make sure you have configured the correct [32-bit Python 2.7.13](https://www.python.org/ftp/python/2.7.13/python-2.7.13.msi) Lib-directory).
2. Insert the API_Key.js by right-click the script in SLCB.
3. Reload all scripts, so the new API_Key.js file gets picked up.
4. Create a `Config.ini` in the script folder:

## Queue Commands

`!<currencyname> queue start <cost>|stop`

`!<currencyname> queue pick <number of users>`

`!<currencyname> queue list`

### User Commands

`!<currencyname> queue enter|leave`

## Example Config.ini

```INI
[Foo]
Command = foo
Cooldown = 1
Database = foo.db

[Bar]
Command = bar
Cooldown = 1
Database = bar.db

[Rewards]
000000000-0000-0000-0000-000000000000 = !foo add {user} 1000
000000000-0000-0000-0000-000000000001 = !bar add {user} 1
000000000-0000-0000-0000-000000000002 = !foo add +viewers 1000

[Defaults]
AddToUser = {broadcaster} --> Successfully given {user} {amount} {currency}
RemoveFromUser = {broadcaster} --> Successfully removed {amount} {currency} from {user}
AddToViewers = {broadcaster} --> {action} giving {amount} {currency} to {group} in chat
RemoveFromViewers = {broadcaster} --> {action} removing {amount} {currency} to {group} in chat
Response = {user}: {amount} {currency}
EnterQueue = {user} entered the {currency} queue at pos {position}
LeaveQueue = {user} left the {currency} queue
PickQueue = @{broadcaster} the following {amount} users was selected: {users}
OpenQueue = {broadcaster} opened the queue. Use !{currency} queue enter to join for {cost} {currency}
CloseQueue = {broadcaster} closed the queue. You can still leave the queue with !{currency} queue leave
```

The options under `[Defaults]` can to each of the individual currencies, to override the defaults values.

You can not name your currency to Reward nor Defaults, as those are reserved words.
