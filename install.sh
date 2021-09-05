#! /bin/sh

bin_dir=`dirname $0`
bin_dir=`cd $bin_dir && pwd`
echo "Current install dir: $bin_dir"

# Create configure directory.
config_dir="/etc/winctp"
if [ -e $config_dir ]; then
    read -p "Found an existing installation, this is going to cover it, do you approve? Y(y)/N(n)/B(b): " ok
    if [ "$ok" = "N" -o "$ok" = "n" ]; then
        exit 1
    elif [ "$ok" = "B" -o "$ok" = "b" ]; then
        random=`head -200 /dev/urandom | cksum | awk '{print $1}'`
        old_dir="$config_dir-$random"
        echo -n "The old installation has been bakuped at: $old_dir... "
        mv $config_dir $old_dir
        [ $? -ne 0 ]  &&  echo "[ FAIL ]" && exit 1
        echo "[ OK ]"
    elif [ "$ok" != "Y" -a "$ok" != "y" ]; then
        echo "Got input '$ok', but only Y(y)/N(n) is allowed, exit."
        exit 1
    fi
fi
mkdir -p $config_dir
[ ! -e $config_dir ] && echo "Make sure root privilege to create configure dir: $config_dir" && exit 1

# Create log directory.
log_dir=/var/log/winctp
[ ! -e "$log_dir/md" ] && echo "Creating log dir for md..." && mkdir -p "$log_dir/md"
[ ! -e "$log_dir/trd" ] && echo "Creating log dir for trd..." && mkdir -p "$log_dir/trd"
[ ! -e $log_dir ] && echo "Failed to create log dir: $log_dir" && exit 1

# Create credentials file.
echo -n "Creating 'credentials' files... "
cat << EOF > $config_dir/credentials
[shinnytech]
account =
passwd =

[broker]
broker_id =
account_id =
password =
EOF
[ $? -ne 0 ]  &&  echo "[ FAIL ]" && exit 1
echo "[ OK ]"

# Create global file.
echo -n "Creating 'global' files... "
cat << EOF > $config_dir/global
[globals]
log_dir = $log_dir
md_runtime_dir =
trade_details_dir =
trader_config_dir =
market_data_dir =

[daemon]
trade_time = 8:55~11:35, 20:55~2:35
#replay_time = 19:00

[mdsrv]
start_time = 20:30
stop_time = 15:30
# Debug level: 10 -> debug，20 -> info, 30 -> warning, 40 -> error, 50 -> critical/fatal
debug_level = 20
EOF
[ $? -ne 0 ]  &&  echo "[ FAIL ]" && exit 1
echo "[ OK ]"

# Create trader tasks file.
echo -n "Creating 'trd_tasks' files... "
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
[ $? -ne 0 ]  &&  echo "[ FAIL ]" && exit 1
echo "[ OK ]"

# Create market-data tasks file.
echo -n "Creating 'md_tasks' files... "
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
[ $? -ne 0 ]  &&  echo "[ FAIL ]" && exit 1
echo "[ OK ]"

# Generate ctp_md_srv system service.
CTP_MD_SRV=/etc/systemd/system/ctp_md_srv.service
if [ -e $CTP_MD_SRV ]; then
    echo -n "Found an old installation for ctp_md_srv, remove and reinstall... "
    systemctl disable ctp_md_srv.service
    echo "[ OK ]"
fi

echo -n "Creating ctp_md_srv service... "
cat << EOF > $CTP_MD_SRV
[Unit]
Description = ctp_md_srv (WinCTP service)

[Service]
Type=simple
ExecStart = $bin_dir/md_srv.py
ExecStop = /bin/kill -INT \$MAINPID
TimeoutStopSec = 120
WorkingDirectory = $log_dir
Restart = always
RestartSec = 300

[Install]
WantedBy = multi-user.target
EOF
[ $? -ne 0 ]  &&  echo "[ FAIL ]" && exit 1
echo "[ OK ]"
chmod 644 $CTP_MD_SRV

# Add into init services.
echo -n "Adding ctp_md_srv to init services... "
systemctl enable ctp_md_srv.service
[ $? -ne 0 ]  &&  echo "[ FAIL ]" && exit 1
echo "[ OK ]"

cat << EOF

    WinCTP (ctp_md_srv service) has been installed successfully!
    Please fill the configurations at $config_dir before start the service,
    then start the service as below,

        sudo systemctl start ctp_md_srv.service

     Or stop the service,

        sudo systemctl stop ctp_md_srv.service

EOF
