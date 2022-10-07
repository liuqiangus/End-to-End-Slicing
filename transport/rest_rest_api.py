from flask import request, url_for
from flask_api import FlaskAPI, status, exceptions
import copy

app = FlaskAPI(__name__)

DATABASE = {
    'slice1':{
                    '172.15.0.2':{
                        'bandwidth':10,
                        'static_path':1
                    }, 
                    '172.15.0.4':{
                        'bandwidth':10,
                        'static_path':0
                    }
            },
    'slice2':{
                    '172.15.0.6':{
                        'bandwidth':5,
                        'static_path':0
                    }
            },
    'slice3':{
                    '172.15.0.8':{
                        'bandwidth':20,
                        'static_path':0
                    }
            },
}

BACKUP = copy.deepcopy(DATABASE) # as backup


def create_database_with_request(request):
    global DATABASE

    data = request.data # get data from 

    try:
  
        for s_key in data.keys(): # loop for slices
            if s_key not in DATABASE.keys(): DATABASE[s_key] = {}

            for u_key in data[s_key].keys():  # loop for users
                if u_key not in DATABASE[s_key].keys(): DATABASE[s_key][u_key] = {}

                for c_key in data[s_key][u_key].keys(): # loop for config
                    DATABASE[s_key][u_key][c_key] = data[s_key][u_key][c_key]
    
        return True

    except:

        return False

def update_database_with_request(request):
    global DATABASE

    data = request.data # get data from 

    try:
  
        for s_key in data.keys(): # loop for slices
            for u_key in data[s_key].keys():  # loop for users
                for c_key in data[s_key][u_key].keys(): # loop for config
                    if c_key in DATABASE[s_key][u_key].keys(): # if matched, update DATABASE
                        DATABASE[s_key][u_key][c_key] = data[s_key][u_key][c_key]
    
        return True

    except:

        return False


def delete_database_with_request(request):
    global DATABASE, BACKUP
    
    DATABASE = copy.deepcopy(BACKUP)

    return True



@app.route("/", methods=['GET', 'PUT', 'POST', 'DELETE'])
def function():
    """
    List or update DATABASE.
    """
    global DATABASE

    if request.method == 'PUT':
        
        if_success = update_database_with_request(request)

        if if_success:
            return DATABASE, status.HTTP_202_ACCEPTED
        else:
            return DATABASE, status.HTTP_400_BAD_REQUEST

    elif request.method == 'POST':
        
        if_success = create_database_with_request(request)

        if if_success:
            return DATABASE, status.HTTP_201_CREATED
        else:
            return DATABASE, status.HTTP_400_BAD_REQUEST
    
    elif request.method == 'DELETE':

        if_success = delete_database_with_request(request)

        if if_success:
            return DATABASE, status.HTTP_205_RESET_CONTENT
        else:
            return DATABASE, status.HTTP_400_BAD_REQUEST
    else:
        # request.method == 'GET'
        return DATABASE, status.HTTP_200_OK


# @app.route("/<int:key>/", methods=['GET', 'PUT', 'DELETE'])
# def database_detail(key):
#     """
#     Retrieve, update or delete note instances.
#     """
#     if request.method == 'PUT':
#         note = str(request.data.get('text', ''))
#         database[key] = note
#         return note_repr(key)

#     elif request.method == 'DELETE':
#         database.pop(key, None)
#         return '', status.HTTP_204_NO_CONTENT

#     # request.method == 'GET'
#     if key not in database:
#         raise exceptions.NotFound()
#     return note_repr(key)


if __name__ == "__main__":
    app.run(debug=True)