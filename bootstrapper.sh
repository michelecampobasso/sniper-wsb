#!/bin/bash

pkill telegram-cli
sleep 1

# Although not necessary, it happens sometimes something odd.
if [[ -f "/tmp/new_coins" ]] ; then
	rm /tmp/new_coins
fi

if [[ ! -f "executed_sales.json" ]] ; then
	echo "[]" > executed_sales.json
fi

if [[ ! -f "executed_trades.json" ]] ; then
	echo "[]" > executed_sales.json
fi

telegram-cli | grep --line-buffered "The coin we have picked to pump today is " | awk -F'#' '{print $2; fflush();}' | tee /tmp/new_coins &
sleep 1
python3 main.py
