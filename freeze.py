# -*- coding: utf8 -*-

from flask_frozen import Freezer
from of_hh import app

freezer = Freezer(app)


if __name__ == '__main__':
	freezer.freeze()
