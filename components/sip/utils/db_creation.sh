#!/bin/bash

# Define MySQL root credentials
MYSQL_ROOT_USER="root"
MYSQL_ROOT_PASSWORD=$KAM_DB_PWD
KAMAILIO_DB_NAME=$KAM_DB_USER
CHARSET=$KAM_DB_CHARSET

CMD_SEQ=$(cat <<EOF
$MYSQL_ROOT_PASSWORD
$CHARSET
y
y
y
EOF
)

# Function to check if the Kamailio database exists
check_db_exists() {
    echo "Checking if the Kamailio database exists..."
    DB_EXISTS=$(mysql -u $MYSQL_ROOT_USER -p$MYSQL_ROOT_PASSWORD -e \
    "SHOW DATABASES LIKE '$KAMAILIO_DB_NAME';" | \
    grep "$KAMAILIO_DB_NAME" > /dev/null; echo "$?")
    return "$DB_EXISTS"
}

# Function to create the Kamailio database
create_kamailio_db() {
    echo "Creating Kamailio database..."
    # Run the kamdbctl command to create the database
    kamdbctl create <<<"$CMD_SEQ"
    echo "Kamailio database creation completed."
}

if check_db_exists; then
    echo "The Kamailio database already exists. Skipping creation."
else
    create_kamailio_db
fi
