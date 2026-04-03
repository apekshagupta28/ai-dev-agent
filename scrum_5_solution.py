from flask import Flask, request, render_template_string

app = Flask(__name__)

template = """
<html>
    <body>
        <h2>Login Page</h2>
        <form action="/login" method="post">
            <label for="username">Username:</label><br>
            <input type="text" id="username" name="username" required><br>
            <label for="password">Password:</label><br>
            <input type="password" id="password" name="password" required><br>
            <input type="submit" value="Submit">
        </form>
    </body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        return f'Username: {username}, Password: {password}'
    return render_template_string(template)

if __name__ == '__main__':
    app.run()