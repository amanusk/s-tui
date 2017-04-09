#!/bin/bash
	i=0
	for line in `grep "cpu MHz" /proc/cpuinfo | cut -d ":" -f 2 | cut -d "." -f 1`; do
		echo "CPU $i: $line "
		let i=$i+1
	done
	sum=$(for line in `grep "cpu MHz" /proc/cpuinfo`; do
	echo "$line" | sed -e '/cpu/d' -e '/MHz/d' -e '/:/d' | cut -d '.' -f1; done | paste -sd+ - | bc)
	cores=$(grep "cpu MHz" /proc/cpuinfo | wc -l)
	echo "Avg Clk: $(($sum/$cores)) MHz"
	# Show memory usage
	free -m | awk 'NR==2{printf "Memory Usage: %s/%sMB (%.2f%%)\n", $3,$2,$3*100/$2 }'
	# Show fan speed
	echo "Fan: `sensors | grep fan1 | awk '{print $2}'` RPM"
	# Show cpu temp
	echo "CPU Temp: `sensors | grep temp1 | awk '{print $2}'`"
