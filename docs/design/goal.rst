Goal
====

Earth Reader aims to decentralize feed reader ecosystem which had been highly
centralized to Google Reader.  Google Reader had changed the world of news
readers, from desktop apps to web-based services.

However `Google Reader shut down on July 1, 2013.`__  Everyone panicked,
several new feed reader services were born, users had to migrate their data,
and the most of alternative services were not able to import starred and
read data, but just subscription list through OPML.

`Feed readers are actually desktop apps at first.`__  A few years later
some people had started to lose their data, because desktop apps had simply
stored data to local disk.  In those days there were already some web-based feed
readers e.g. Bloglines_, Google Reader, but they provided worse experience
than desktop apps (there were no Chrome, and JavaScript engines were way slower
back then).  Nevertheless people had gradually moved to web-based services
from desktop apps, because they never (until the time at least) lost data,
and were easily synchronized between multiple computers.

These feed reader services are enough convenient, but always have some risk
that you can't control your own data.  If the service you use suddenly shut
down without giving you a chance to backup data, you would have to start
everything from scratch.  Your starred articles would be gone.

The goal of Earth Reader is to achieve the following subgoals at the same time:

- The whole data should be controlled by the owner.  It means data will be
  tangible and reachable on the file system.
- It should be possible to synchronize data between multple devices, without
  any conflict between simultaneous updates.
- The implementation and data format should be open and free.
- It could provide native apps for the most of major platforms.

__ http://googlereader.blogspot.com/2013/03/powering-down-google-reader.html
__ https://minhee.quora.com/RSS-readers-had-been-originally-desktop-apps
.. _Bloglines: http://www.bloglines.com/
