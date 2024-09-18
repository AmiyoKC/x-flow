# x-flow
A Spotify playlist generator for distance runners

The app is written using Flask and Spotify APIs. I also use redis for session management. 

The app takes age, distance of the run, duration of the run along with genres you are interested in as input (last is a multi-select). 

Spotify authorization flow is used to authenticate users, and once authenticated a link to a playlist is made available. 

The premise behind the app is that the your heart rate tends to match the tempo of the music you are listening to. A good workout should take you to about 80% of your max heart rate (an age dependent number). The songs in the generated playlist are sequenced such that you start gently and gradually build up your heart rate. 

App can be acccessed from [https://x-flow.onrender.com/] (hosted on render at the moment). It's on render's free tier, which spins down the app if there is prolonged inactivity so depending on when you access, so depending on when you access the link there might be some lag in brining up the service. 
