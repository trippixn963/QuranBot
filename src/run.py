from src.monitoring.logging.logger import logger, log_tree_start, log_tree_item, log_tree_end

# Replace startup validation logs with tree style:
log_tree_start("Environment Validation")
log_tree_item("✅ Working directory validated")
log_tree_item("✅ Required directories checked")
log_tree_item("✅ Exception handling configured", is_last=True)
log_tree_end()

# Replace startup completion logs with tree style:
log_tree_start("QuranBot Startup Complete")
log_tree_item("📦 Bot modules imported")
log_tree_item("🎯 Bot instance created")
log_tree_item("🚀 Bot started successfully", is_last=True)
log_tree_end()

# Replace shutdown logs with tree style:
log_tree_start("QuranBot Shutdown")
log_tree_item("🛑 Graceful shutdown initiated")
log_tree_item("💾 State saved")
log_tree_item("🔌 Connections closed", is_last=True)
log_tree_end() 