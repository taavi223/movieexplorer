/**
* Main AngularJS Web Application
*/


var app = angular.module('movieExplorer', ['ngRoute', 'ui.bootstrap']);

/**
* Configure the Routes
*/
app.config(['$routeProvider', function ($routeProvider) {
$routeProvider
.when("/", {templateUrl: "partials/instructions.html"})
.when("/explore", {templateUrl: "partials/explore.html", controller: "Explore"})
.otherwise("/404", {templateUrl: "partials/404.html"});
}]);

function chunk(arr, size) {
  var newArr = [];
  for (var i=0; i<arr.length; i+=size) {
    newArr.push(arr.slice(i, i+size));
  }
  return newArr;
}

/**
* Controls MovieExplorer
*/
app.controller('Explore', function ($scope, $route, $http, $timeout, $anchorScroll, $window, $uibModal) {
  var candidateHistory = [];
  var candidates = [];
  var feedbackHistory = [];
  var feedback = {};
  var excludeHistory = [];
  var exclude = [];
  
  $scope.buttonsDisabled = false;
  $scope.expandRoundDisabled = false;
  $scope.errorMessage = false;
  $scope.rounds = []
  $scope.candidateRows = []
  
  $http.post('/api', {"rounds": []}).then(
    function(response) {
      var data = response.data;
      
      // Set candidates
      candidates = data.candidates;
      candidates.forEach(function(candidate, index) {feedback[candidate.item_index] = 0;});
      $scope.candidateRows = chunk(candidates, 5);
      
      $timeout(function() { $anchorScroll('end', 0, false); }) 
    }, function(response) {
      $scope.errorMessage = 'Unable to start session.';
    }
  );
  
  $scope.prefIsSet = function(item_index, preference) {
    return feedback[item_index] == preference;
  };

  $scope.setPref = function(item_index, preference) {
    if (feedback[item_index] == preference) {
      feedback[item_index] = 0;
    } else {
      feedback[item_index] = preference;
    }
  };

  $scope.newSession = function() {
    $route.reload();
  };

  $scope.modal = function(movie) {
    $uibModal.open({
      templateUrl: 'partials/movie-modal.html',
      size: "md",
      controller: function ModalInstanceCtrl ($uibModalInstance, $sce, movie) {
        var $ctrl = this;
        $ctrl.movie = movie;
        $ctrl.fullPosterPath = $sce.trustAsResourceUrl('//image.tmdb.org/t/p/w342' + $ctrl.movie.posterPath);
        if ($ctrl.movie.genres && $ctrl.movie.genres.length > 4) {
          $ctrl.movie.genres = $ctrl.movie.genres.slice(0, 4);
        }
        if ($ctrl.movie.actors && $ctrl.movie.actors.length > 6) {
          $ctrl.movie.actors = $ctrl.movie.actors.slice(0, 6);
        }
        if ($ctrl.movie.youtubeTrailerIds[0]) {
          $ctrl.ytUrl = $sce.trustAsResourceUrl('//www.youtube.com/embed/' + $ctrl.movie.youtubeTrailerIds[0] + '?fs=1');
        }
      },
      controllerAs: '$ctrl',
      resolve: {
        movie: function () {
          return movie;
        }
      }
    })
  };

  $scope.nextRound = function() {
    $scope.buttonsDisabled = true;
    var newFeedbackHistory = feedbackHistory.slice(0);
    newFeedbackHistory.push(feedback);
    
    console.log(JSON.stringify(exclude));
    $http.post('/api', {"rounds": newFeedbackHistory, "exclude": exclude}).then(
      function(response) {
        feedbackHistory = newFeedbackHistory;
        candidateHistory.push(candidates);
        excludeHistory.push(exclude);

        // Add new round to existing rounds.
        var round = {
          "number": $scope.rounds.length + 1,
          "movies": {
            "1": candidates.filter(function(cand) {return feedback[cand.item_index] == 1}),
            "0": candidates.filter(function(cand) {return feedback[cand.item_index] == 0}),
            "-1": candidates.filter(function(cand) {return feedback[cand.item_index] == -1}),
          }
        }
        $scope.rounds.push(round)

        /////////////////////////
        
        var data = response.data;
    
        // Reset preference data and zero out preference data for new candidates.
        feedback = {};
        candidates = data.candidates;
        data.candidates.forEach(function(candidate, index) {feedback[candidate.item_index] = 0;});
        $scope.candidateRows = chunk(candidates, 5);
    
        // Re-enable the submit button and expand round button.
        $scope.buttonsDisabled = false;
        $scope.expandRoundDisabled = false;
        $scope.errorMessage = false;
        $timeout(function() { $anchorScroll('end', 0, false); })
      }, function(response) {
        $scope.buttonsDisabled = false;
        $scope.errorMessage = 'Unable to save round.';
      }
    );
  };

  $scope.previousRound = function(target) {
    target = target - 1;
    
    // Set candidates, feedback, and exclude parameters appropriately
    candidates = candidateHistory[target];
    candidateHistory = candidateHistory.slice(0, target);
    feedback = feedbackHistory[target];
    feedbackHistory = feedbackHistory.slice(0, target);
    exclude = excludeHistory[target];
    excludeHistory = excludeHistory.slice(0, target);
    
    // Remove old rounds and update the candidate rows.
    $scope.rounds = $scope.rounds.slice(0, target);
    $scope.candidateRows = chunk(candidates, 5);
  };

  $scope.refreshRound = function() {
    var dirty = Object.keys(feedback)
      .map(key => Math.abs(feedback[key]))
      .reduce((a, b) => a + b, 0);

    var answer = true;
    if (dirty) {
      answer = $window.confirm('If you refresh this round, the preferences you have set for these movies will be lost. Are you sure you want to continue?');
    }

    if (answer) {
      newExclude = Object.keys(feedback).map(Number);
      newExclude.push.apply(newExclude, exclude);

      $scope.buttonsDisabled = true;
      $http.post('/api', {"rounds": feedbackHistory, "exclude": newExclude}).then(
        function (response) {
          var data = response.data;
  
          // Replace previous candidates with new candidates.
          candidates = data.candidates;
          $scope.candidateRows = chunk(candidates, 5);

          // Zero out preference data for new candidates.
          feedback = {};
          candidates.forEach(function (candidate, index) {
            feedback[candidate.item_index] = 0;
          });
          
          exclude = newExclude;
          
          $scope.buttonsDisabled = false;
          $scope.expandRoundDisabled = false;
          $scope.errorMessage = false;
        }, function(response) {
          $scope.buttonsDisabled = false;
          $scope.errorMessage = 'Unable to refresh round.';
        }
      );
    }
  };

  $scope.expandRound = function() {
    $scope.buttonsDisabled = true;
    
    $http.post('/api', {"rounds": feedbackHistory, "exclude": Object.keys(feedback).map(Number)}).then(
      function(response) {
        var data = response.data;
  
        // Zero out preference data for new candidates.
        data.candidates.forEach(function(candidate, index) {feedback[candidate.item_index] = 0;});
  
        // Add new candidates to previoius candidates
        candidates = candidates.concat(data.candidates);
        $scope.candidateRows = chunk(candidates, 5);
  
        $scope.buttonsDisabled = false;
        $scope.expandRoundDisabled = true;
        $scope.errorMessage = false;
        $timeout(function() { $anchorScroll('end', 0, false); })
      }, function(response) {
        $scope.buttonsDisabled = false;
        $scope.errorMessage = 'Unable to add more movies to round.';
      }
    );
  }; 
});
