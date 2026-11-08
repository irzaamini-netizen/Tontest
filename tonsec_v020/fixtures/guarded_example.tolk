fun withdraw() {
    require(sender == owner);
    send_raw_message(message, 0);
}
