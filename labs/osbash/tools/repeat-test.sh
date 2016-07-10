#!/bin/bash
set -o errexit -o nounset
TOP_DIR=$(cd "$(dirname "$0")/.." && pwd)
source "$TOP_DIR/config/localrc"
source "$TOP_DIR/config/paths"
source "$CONFIG_DIR/deploy.osbash"
source "$OSBASH_LIB_DIR/functions-host.sh"
source "$OSBASH_LIB_DIR/$PROVIDER-functions.sh"

if [ -f "$TOP_DIR/osbash.sh" ]; then
    BUILD_EXE=$TOP_DIR/osbash.sh
    OSBASH=exec_cmd
elif [ -f "$TOP_DIR/st.py" ]; then
    BUILD_EXE=$TOP_DIR/st.py
else
    echo "No build exe found."
    exit 1
fi

echo "Using $BUILD_EXE"

LOG_NAME=test.log
RESULTS_ROOT=$LOG_DIR/test-results

CONTROLLER_SNAPSHOT="controller_node_installed"
# TODO Add better method for setting TEST_SCRIPT
TEST_SCRIPT=$TOP_DIR/scripts/test/launch_instance_private_net.sh

VERBOSE=${VERBOSE:=1}

function usage {
    echo "Usage: $0 {-b|-c|-t <SNAP>} [-s '<NODES>']"
    echo ""
    echo "-h        Help"
    echo "-c        Restore node VMs to current snapshot for each test"
    echo "-t SNAP   Restore cluster to target snapshot for each test"
    echo "-r REP    Number of repetitions (default: endless loop)"
    echo "-s NODES  Start each named node VM after restoring the cluster"
    echo "-b        Rebuild cluster for each test, from scratch or snapshot"
    echo "          ($(basename $BUILD_EXE) -b cluster [...])"
}

while getopts :bchr:s:t: opt; do
    case $opt in
        b)
            REBUILD=yes
            ;;
        c)
            CURRENT=yes
            ;;
        h)
            usage
            exit 0
            ;;
        r)
            REP=$OPTARG
            ;;
        s)
            START_VMS=$OPTARG
            ;;
        t)
            arg=$OPTARG
            for node in $(script_cfg_get_nodenames); do
                if vm_exists "$node"; then
                    if vm_snapshot_exists "$node" "$arg"; then
                        TARGET_SNAPSHOT=$arg
                        break
                    fi
                fi
            done
            if [ -z "${TARGET_SNAPSHOT:-""}" ]; then
                echo >&2 "No snapshot named $arg found."
                exit 1
            fi
            ;;
        :)
            echo "Error: -$OPTARG needs argument"
            ;;
        ?)
            echo "Error: invalid option -$OPTARG"
            echo
            usage
            exit 1
            ;;
    esac
done

if [ -z "${REBUILD:-}" -a -z "${CURRENT:-}" -a -z "${TARGET_SNAPSHOT:-}" ]; then
    usage
    exit 1
fi

# Remove processed options from arguments
shift $(( OPTIND - 1 ));

mkdir -p "$RESULTS_ROOT"

# Default to repeating forever
: ${REP:=-1}

cnt=0
until [ $cnt -eq $REP ]; do
    cnt=$((cnt + 1))

    dir_name=$(get_next_prefix "$RESULTS_ROOT" "")
    echo "####################################################################"
    echo "Starting test $dir_name."
    dir=$RESULTS_ROOT/$dir_name
    mkdir -p "$dir"

    (
    cd "$TOP_DIR"

    if [ -n "${TARGET_SNAPSHOT:-}" ]; then
        "$TOP_DIR/tools/restore-cluster.sh" -t "$TARGET_SNAPSHOT"
        if [ -n "${START_VMS:-}" ]; then
            # Start VMs as requested by user
            for vm_name in $START_VMS; do
                echo >&2 "$0: booting node $vm_name."
                vm_boot "$vm_name"
                # Sleeping for 10 s fixes some problems, but it might be
                # better to fix client scripts to wait for the services they
                # need instead of just failing.
            done
        fi
    fi

    rc=0
    if [ -n "${REBUILD:-}" ]; then
        if [ -n "${TARGET_SNAPSHOT:-}" ]; then
            LEAVE_VMS_RUNNING=yes "$BUILD_EXE" -t "$TARGET_SNAPSHOT" -b cluster || rc=$?
        else
            "$BUILD_EXE" -b cluster || rc=$?
        fi
    fi
    echo "####################################################################"

    if [ $rc -ne 0 ]; then
        echo "ERROR: Cluster build failed. Skipping test."
    else
        echo "Running test. Log file: $LOG_DIR/$LOG_NAME"
        TEST_ONCE=$TOP_DIR/tools/test-once.sh
        if [ "${VERBOSE:-}" -eq 1 ]; then
            "$TEST_ONCE" "$TEST_SCRIPT" 2>&1 | tee "$LOG_DIR/$LOG_NAME" || rc=$?
        else
            "$TEST_ONCE" "$TEST_SCRIPT" > "$LOG_DIR/$LOG_NAME" 2>&1 || rc=$?
        fi

        echo "################################################################"
        if [ $rc -eq 0 ]; then
            echo "Test passed."
        else
            echo "ERROR: Test failed."
        fi
    fi
    )

    echo "Copying osbash and test log files into $dir."
    (
    cd "$LOG_DIR"
    cp -a *.auto *.log *.xml *.db "$dir" || rc=$?
    )

    echo "Copying upstart log files into $dir."
    "$TOP_DIR/tools/get_node_logs.sh" "$dir"
done
