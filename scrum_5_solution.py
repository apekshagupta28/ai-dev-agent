from flask import Flask, request, render_template_string

app = Flask(__name__)

template = """
<html>
    <body>
        <h1>Login Page</h1>
        <form action=/login method=post>
            <label>Username:</label>
            <input type=text name=username><br>
            <label>Password:</label>
            <input type=password name=password><br>
            <input type=submit value=Login>
        </form>
    </body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        return f'Username: {username}, Password: {password}'
    return render_template_string(template)

if __name__ == '__main__':
    app.run(debug=True)