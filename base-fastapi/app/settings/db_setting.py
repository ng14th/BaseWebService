class DatabaseSetting:
    # Variables for the database
    use_pgbouncer: bool = False

    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "admin"
    db_pass: str = ""
    db_name: str = "my-app"
    db_echo: bool = False

    db_timeout: int = 10
    db_pool_size: int = 20
    db_max_overflow: int = 40
    db_pool_timeout: int = 30
    db_pool_pre_ping: bool = True
    db_pool_recycle: int = 300

    # Variables for the database read replica
    db_read_host: str = "localhost"
    db_read_port: int = 5432
    db_read_user: str = "admin"
    db_read_pass: str = ""
    db_read_name: str = "my-app"
