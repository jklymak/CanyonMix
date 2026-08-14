import os
import logging
logging.basicConfig(level=logging.INFO)

_log = logging.getLogger(__name__)

for td in ['006', '005', '007']:
    todo = f'Slope2D{td}'
    _log.info(f'Running {todo}')
    os.system(f'cd ../results/{todo}/input && mpirun -np 8 ../build/mitgcmuv')
    os.system(f'cd /Users/jklymak/Dropbox/CanyonMix/input')
    _log.info(f'Done {todo}')


if False:
    num = 0
    sp = '060'
    for alpha in ['70', '100', '125']:
        todo = f'StraightSlopeTightDyehfacconstN200alpha{alpha}u090'
        _log.info(f'Running {todo}')
        os.system(f'cd ../results/{todo}/input && mpirun -np 8 ../build/mitgcmuv')
        os.system(f'cd /Users/jklymak/Dropbox/CanyonMix/input')
        _log.info(f'Done {todo}')

    for td in ['70', '100', '125']:
        for sp in ['030', '060']:
            if num > 0:
                todo = f'StraightSlopeconstN200alpha{td}u{sp}'
                _log.info(f'Running {todo}')
                os.system(f'cd ../results/{todo}/input && mpirun -np 8 ../build/mitgcmuv')
                os.system(f'cd /Users/jklymak/Dropbox/CanyonMix/input')
                _log.info(f'Done {todo}')
            num += 1
