function autoLoad() {
     'use strict';

     var counter = 1;

     function addUser() {
          var newUser = document.createElement('div');
          newUser.innerHTML = "Username" + ++counter + ": <input name=s type=text><br>";
          document.getElementById('moreUsers').appendChild(newUser);
     }

     document.getElementById('adduser').onclick = addUser;
}

autoLoad();
