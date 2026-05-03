module.exports = {
  apps: [
    {
      name: "polymarket-copytrade",
      script: "./src/main_copy_trade.py",
      interpreter: "python3",
      cwd: "/home/ey9dyk3j8bg3/polymarket-copy-trade",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      env: {
        NODE_ENV: "production",
        MODE: "prod",
        SIMULATION_MODE: "true",
        LIVE_TRADING: "false",
      },
    },
    {
      name: "polymarket-telegram",
      script: "./src/main_telegram.py",
      interpreter: "python3",
      cwd: "/home/ey9dyk3j8bg3/polymarket-copy-trade",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      env: {
        NODE_ENV: "production",
        MODE: "prod",
        SIMULATION_MODE: "true",
        LIVE_TRADING: "false",
        PYTHONPATH: "./src:./scripts",
      },
    },
  ],
};
