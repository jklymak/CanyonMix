#!/usr/bin/env bash
set -euo pipefail

runs=(Slope2D103 Slope2D104 Slope2D105)
failed_runs=()

for i in "${!runs[@]}"; do
	runname="${runs[$i]}"
	rundir="results/${runname}/input"

	if [[ ! -d "$rundir" ]]; then
		echo "Skipping ${runname}: missing ${rundir}"
		continue
	fi

	echo "Running ${runname}..."
	if (
		cd "$rundir"
		rm -f -- ./*.data ./*.meta
		mpirun -np 8 ../build/mitgcmuv > "/tmp/${runname}.log" 2>&1
	); then
		echo "Completed ${runname}"
	else
		echo "Failed ${runname}; see /tmp/${runname}.log"
		failed_runs+=("$runname")
	fi

	if (( i < ${#runs[@]} - 1 )); then
		echo "Sleeping 600 seconds before next run..."
		sleep 600
	fi
done

if (( ${#failed_runs[@]} > 0 )); then
	echo "Runs failed: ${failed_runs[*]}"
	exit 1
fi

echo "All runs completed successfully"
