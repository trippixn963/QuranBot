"""
Tree-structured logging utility for QuranBot.
Provides hierarchical, readable logs with connect symbols (├─, └─) for context.
Usage: tree_log('info', 'Message', {'key': 'value', ...})
"""
import logging
import sys
import traceback

def _tree_format(d, prefix="", is_last=True):
    """Recursively format a dictionary as a tree with connect symbols."""
    lines = []
    try:
        if not isinstance(d, dict):
            return [prefix + str(d)]
        items = list(d.items())
        for i, (k, v) in enumerate(items):
            connector = "└─ " if i == len(items) - 1 else "├─ "
            new_prefix = prefix + ("   " if i == len(items) - 1 else "│  ")
            if isinstance(v, dict):
                lines.append(f"{prefix}{connector}{k}:")
                lines.extend(_tree_format(v, new_prefix, True))
            else:
                lines.append(f"{prefix}{connector}{k}: {v}")
    except Exception as e:
        from src.monitoring.logging.tree_log import tree_log
        tree_log('error', 'tree_log: Error formatting tree', {'error': str(e), 'traceback': traceback.format_exc()})
    return lines

def tree_log(level, message, tree_dict=None, logger=None):
    """
    Log a message in a tree/structured format with connect symbols for context.
    Usage: tree_log('error', 'Failed to connect', {'host': 'localhost', ...})
    """
    try:
        if logger is None:
            logger = logging.getLogger()
        log_func = getattr(logger, level, logger.info)
        log_func(message)
        if tree_dict is not None:
            for line in _tree_format(tree_dict):
                log_func(line)
    except Exception as e:
        from src.monitoring.logging.tree_log import tree_log
        tree_log('error', 'tree_log: Error logging tree', {'error': str(e), 'traceback': traceback.format_exc()})

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.DEBUG)
    tree_log('info', 'Example tree log', {'user': 'test', 'action': 'login', 'details': {'ip': '127.0.0.1', 'success': True}}) 