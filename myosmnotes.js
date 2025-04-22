var counter = 1;
function addUser() {
     'use strict';
     var newUser = document.createElement('div');
     newUser.innerHTML = "Username" + ++counter + ": <input name=s type=text><br>";
     document.getElementById('moreUsers').appendChild(newUser);
}
