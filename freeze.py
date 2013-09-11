# -*- coding: utf8 -*-

from flask_frozen import Freezer
from of_hh import app


#app.config['FREEZER_BASE_URL'] = '/'
app.config['FREEZER_RELATIVE_URLS'] = True

freezer = Freezer(app)

if __name__ == '__main__':
	freezer.freeze()
