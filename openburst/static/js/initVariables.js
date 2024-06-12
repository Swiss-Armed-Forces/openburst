var proxy_server; //----------- "proxy_server" ist set by webserver.py and initialized when the html page is called

function add_proxy_server(val) {
  console.log("adding burst proxy server: ", val);
  proxy_server = val;
}

var team;
function init_team(val) {
  console.log("initing team: ", val);
  team = val;
}

var node;
function init_node(val) {
  console.log("initing node: ", val);
  node = val;
}
