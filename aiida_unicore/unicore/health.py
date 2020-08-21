'''
Created on May 13, 2019

@author: Tim Kreuzer
@mail: t.kreuzer@fz-juelich.de
'''

from flask_restful import Resource

class HealthHandler(Resource):
    def get(self):
        return '', 200