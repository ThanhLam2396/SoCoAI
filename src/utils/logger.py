import logging

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    
    if not logger.hasHandlers():
        logger.addHandler(handler)
    
    logger.propagate = False
    
    root_logger = logging.getLogger()  # Root logger
    if root_logger.handlers:
        logger.info(f"Root logger has handlers: {root_logger.handlers}")
    else:
        logger.info("Root logger has no handlers")
    
    return logger