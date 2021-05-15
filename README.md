# ynvest-tube-server

# Table of contests

<hr>

- [Instruction](#instruction)
- [Endpoints](#endpoints)
    - [register](#register)
        - [GET](#get)

## Instruction

<hr>

`pip install -r requirements.txt`

`./manage.py makemigrations`
`./manage.py migrate`
`./manage.py runserver`

Server is bind to local `http://127.0.0.1:8000/`

## Endpoints

<hr>

### register

`http://127.0.0.1:8000/register`

##### GET

Returns json with unique UUID, and insert such a user to a database.
![](.README_images/uuid.png)