(function(){
    var app = angular.module('nodeup', []);

    app.controller('UserAgentController', ['$http', '$log', '$location', '$window', function($http, $log, $location, $window){
        var agent = this;

        agent.newIdentity = function(){
            $window.location.href = '/?' + Math.random();  // note, the '?' is important here if we want to get entropy from urandom
        }

        agent.uid = $location.path().substr(1);  // remove '/' at beginning of path
        agent.msgs = [];
        agent.email = '';
        agent.emailNotify = false;
        agent.initial = true;
        agent.totalMinutesPaid = 0;
        agent.totalCoinsPaid = 0;

        agent.tip = 10;
        agent.exchangeRate = 100000000000;
        agent.nodeMinutes = 0;


        agent.firstName = '';

        agent.renderGreeting = function(){
            if (agent.firstName == ''){ return "Hello," }
            return "Hello " + agent.firstName + ",";
        }

        agent.showError = false;
        agent.error = '';

        agent.status = "Waiting for payment...";
        agent.statusSymbol = "spinner";

        agent.clients = ['Bitcoin XT', 'Bitcoin Core'];
        agent.client = agent.clients[0];

        agent.months = 1;
        agent.monthsUp = function(){ agent.months += 1; agent.alertModified(); }
        agent.monthsDown = function(){ agent.months -= 1; if (agent.months < 1){ agent.months = 1; }; agent.alertModified();  }

        agent.price = function(){
            var raw_price = 5.00;
            return agent.months * (1 + agent.tip / 100.0) * raw_price;
        }

        agent.saveField = function(field, data){
            if (field == 'tip') { data = data / 100; }
            $http.post('/api', {method: 'saveField', params: {'field': field, 'value': data, 'uid': agent.uid}})
                .success(function(data){
                    // do something here maybe?
                    $log.log('Saved: ' + 'field' + field + ' ' + data)
                }).error(function(a,b,c,d){$log.log(a);})
        }
        agent.loadField = function(field){
            $http.post('/api', {method: 'loadField', params: {'field': field, 'uid': agent.uid}})
                .success(function(data){
                    value = data['value'];
                    $log.log(data);
                    $log.log('Setting ' + field + ": " + value);
                    if (field == 'email') {
                        agent.email = value;
                    } else if (field == 'emailNotify') {
                        agent.emailNotify = value;
                    } else if (field == 'name') {
                        agent.firstName = value;
                    } else if (field == 'tip') {
                        agent.tip = value * 100;
                    } else if (field == 'client') {
                        agent.client = value;
                    } else if (field == 'months') {
                        agent.email = value;
                    }
                })
        }
        agent.loadField('email');
        agent.loadField('emailNotify');
        agent.loadField('name');
        agent.loadField('tip');
        agent.loadField('client');

        agent.loadStats = function(){
            $http.post('/api', {method: 'getStats', params: {'uid': agent.uid}})
                .success(function(data){
                    agent.exchangeRate = data['exchangeRate'];
                    agent.nodeMinutes = data['nodeMinutes'];
                    agent.totalMinutesPaid = data['totalMinutesPaid'];
                    agent.totalCoinsPaid = data['totalCoinsPaid'];
                    $log.log(data);
                }).error($log.log);
            setTimeout(agent.loadStats, 60 * 1000); // update once a min
        }
        agent.loadStats();

        agent.recompile = function(){
            $http.post('/api', {method: 'recompile', params:{'uid': agent.uid}})
                .success(function(data){
                    agent._updateMsgs();
                })
        }

        agent._paymentQR = new QRCode(document.getElementById("paymentQR"), {
            text: "generating qr code...",
            width: 200,
            height: 200,
            colorDark : "#000000",
            colorLight : "#ffffff",
            correctLevel : QRCode.CorrectLevel.H});
        agent._paymentVisible = false;
        agent.hidePayment = function(){
            agent._paymentVisible = false;
        };
        agent.showPayment = function(newURI){
            agent._paymentVisible = true;
            agent._paymentQR.makeCode(newURI);
            agent._paymentURI = newURI;
        };

        agent.getPaymentDetails = function(){
            agent.hidePayment();
            agent.getPaymentDetailsSilent();
        }
        agent.getPaymentDetailsSilent = function(){
            $http.post('/api', {'method': 'getPaymentDetails', params: {
                'uid': agent.uid,
                'client': agent.client,
                'months': agent.months,
            }}).success(function(data){
                    if('error' in data){
                        agent.showError = true;
                        agent.error = data['error'];
                    } else {
                        $log.log(data);
                        if (agent.initial) { agent.initial = false; }
                        agent.showPayment(data['uri']);
                        agent.status = data['status'];
                    }
                })
                .error(function(error, a,b,c){
                });
        };
        agent.getPaymentDetails();

        agent._alertTimeWait = 1500;
        agent._lastAlertModified = 0;
        agent._queued = false;
        agent.alertModified = function(field){
            if (field == 'email') {
                agent.saveField(field, agent.email);
            } else if (field == 'emailNotify') {
                agent.saveField(field, agent.emailNotify);
            } else if (field == 'name') {
                agent.saveField(field, agent.firstName);
            } else if (field == 'tip') {
                agent.saveField(field, agent.tip);
            } else if (field == 'client') {
                agent.saveField(field, agent.client);
            } else if (field == 'months') {
                agent.saveField(field, agent.email);
            }

            agent.hidePayment();
            $log.log('am');
            now = Date.now();
            delta = now - agent._lastAlertModified;
            if (delta < agent._alertTimeWait) {
                if (!agent._queued){
                    setTimeout(agent.alertModified, agent._alertTimeWait);
                    agent._queued = true;
                   }
            } else {
                agent._alertModified();
                agent._lastAlertModified = now;
                agent._queued = false;
            }
        }
        agent._alertModified = function(){
            $log.log('_am')
            agent.getPaymentDetails();
        }

        agent.randomUpdate = function(){
            agent.alertModified();  // don't call the update directly so we don't interfere too much
            setTimeout(agent.randomUpdate, 60 * 1000); // update every 1 minute regardless
        }

        agent.nMsgs = 10;
        agent._updateMsgs = function(){
            $http.post('/api', {'method': 'getMsgs', params: {'uid': agent.uid, 'n': agent.nMsgs}})
                .success(function(data){
                    agent.msgs = data['msgs'];
                    $log.log(agent.msgs);
                    if (agent.msgs.length > 0) {
                        agent.getPaymentDetailsSilent();
                    }
                }).error($log.log);
        }
        agent.updateMsgs = function(){
            var timeout = 999999999999;
            if (agent.msgs.length == 0){
                timeout = 2000;
            } else {
                timeout = 15000;
            }
            agent._updateMsgs();
            setTimeout(agent.updateMsgs, timeout);
        }
        agent.updateMsgs();
    }]);


    app.controller('TabController', ['$http', '$log', '$location', function($http, $log, $location){
        var tabs = this;

        var current = 'main';
        $location.hash(current);

        tabs.is = function(tabName){
            return current == tabName;
        };

        tabs.set = function(tabName){
            current = tabName;
            $location.hash(tabName);
        };
    }]);


    app.config(function($locationProvider) {
        $locationProvider.html5Mode({enabled: true}).hashPrefix('!');
    });

    app.config( [
        '$compileProvider',
        function( $compileProvider )
        {
            $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto|bitcoin):/);
            // Angular before v1.2 uses $compileProvider.urlSanitizationWhitelist(...)
        }
    ]);
})();