import logging
import logging.handlers

def logging_setup(name, level=logging.DEBUG):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    sysLogFormatter = logging.Formatter(fmt='{0}: %(module)s - %(message)s'.format(name))

    file_handler = logging.FileHandler('/tmp/debug.log')
    file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
    ))
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    syshan = logging.handlers.SysLogHandler(address='/dev/log')
    syshan.setFormatter(sysLogFormatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.addHandler(syshan)
    logger.addHandler(file_handler)
    return logger, file_handler
