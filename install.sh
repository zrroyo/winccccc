#! /bin/sh

bin_dir=`dirname $0`
bin_dir=`cd $bin_dir && pwd`
echo "Current install dir: $bin_dir"

config_dir="/etc/winctp"
if [ -e $config_dir ]; then
    read -p "Found an existing installation, this is going to cover it, do you approve? Y(y)/N(n): " ok
    if [ "$ok" = "N" -o "$ok" = "n" ]; then
        exit 1
    elif [ "$ok" != "Y" -a "$ok" != "y" ]; then
        echo "Got input '$ok', but only Y(y)/N(n) is allowed, exit."
        exit 1
    fi
fi
mkdir -p $config_dir
[ ! -e $config_dir ] && echo "Make sure root privilege to create configure dir: $config_dir" && exit 1

echo "Creating configuration files..."
# Create credentials file.
cat << EOF > $config_dir/credentials
[shinnytech]
account =
passwd =

[broker]
broker_id =
account_id =
password =
EOF

# Create global file.
cat << EOF > $config_dir/global
[globals]
md_runtime_dir =
trade_details_dir =
trader_config_dir =
market_data_dir =

[daemon]
trade_time = 8:55~11:35, 20:55~2:35
#replay_time = 19:00
EOF

# Create trader tasks file.
cat << EOF > $config_dir/trd_tasks
# Each future defines its own parameters as below, for example,
#
#[p2012]
#strategy = turt1
#lot_size_pos = 2
#signal_start = 15
#signal_end = 10
#spThresholds = ((None, None, None, None, None), (3, -0.003, -0.00803, 0.0180, 0.0361), (2, -0.007, -1, 0.04, 0.06), (2, 0, -1, 0.04, 0.08),)
#apThresholds = [None, 0.013, 0.0129, 0.013]
#clThresholds = [-0.016, -0.016, -0.025, -0.03]
#
EOF

# Create market-data tasks file.
cat << EOF > $config_dir/md_tasks
# Each future defines its own parameters as below, for example,
#
#[DCE.p2109]
#duration = 60
#
#[DCE.p2201]
#duration = 60
#
EOF

# Generate ctp_md_srv init service.
CTP_MD_SRV=/etc/init.d/ctp_md_srv
if [ -e $CTP_MD_SRV ]; then
    echo "Found an old installation for ctp_md_srv, remove and reinstall..."
    update-rc.d -f ctp_md_srv remove
fi

echo "Creating ctp_md_srv service..."
cat << EOF > $CTP_MD_SRV
#! /bin/sh
#
# Startup script for ctp_md_srv
#
# description: ctp_md_srv
# processname: ctp_md_srv
# config: $config_dir

CFG_DIR="$config_dir"
INSTALL_DIR=$bin_dir
PROC_NAME="md_srv.py"

if [ ! -d "\$CFG_DIR" ]; then
    echo "CFG_DIR doesn't exist"
    exit 1
elif [ ! -d "\$INSTALL_DIR" ]; then
    echo "INSTALL_DIR doesn't exist"
    exit 1
fi

RETVAL=0

# If PROC_NAME is currently running then return 1, otherwise return 0 instead.
_check_winctp_exist() {
    IfExist=\`ps awx -o command | awk -F/ '{print \$NF}' | grep -x \$PROC_NAME\`
    [ "\$IfExist" != "" ] && return 1
    return 0
}

# See how we were called.
start() {
    echo -n "Starting winctp: "

    _check_winctp_exist
    if [ "\$?" != "0" ]
    then
        echo "\$PROC_NAME is already running"
    else
        "\$INSTALL_DIR/\$PROC_NAME" &
        echo OK
    fi
}

stop() {
    echo -n "Stopping winctp: "

    retry=0
    while [ 1 ]
    do
        _check_winctp_exist
        if [ "\$?" != "0" ]
        then
            if [ "\$retry" -lt 9 ]
            then
                killall -9 \$PROC_NAME > /dev/null 2>&1
            else
                killall -9 \$PROC_NAME
                break
            fi
            sleep 1
            retry=\$((\$retry + 1))
        else
            break
        fi
    done
}

# See how we were called.
case "\$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 5
        start
        ;;
    *)
        echo "Usage: winctp {start|stop|restart}"
        exit 1
esac

exit \$RETVAL
EOF
[ ! -e $CTP_MD_SRV ] && echo "Failed to create $CTP_MD_SRV, exit." && exit 1
chmod 754 $CTP_MD_SRV

# Add into init services.
update-rc.d ctp_md_srv defaults 95
# Start the new service.
service ctp_md_srv restart
