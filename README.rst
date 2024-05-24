Music player for online music
=============================

Disclaimer
----------
The following disclaimer is intended to communicate certain limitations and conditions regarding the use of this project source code.

1. **Educational Purposes Only**:
   - This software is provided for educational purposes only. It is designed to assist users in understanding software development concepts and should not be used for commercial or production purposes.

2. **Compliance with Service Providers' Terms of Use**:

   - This software interacts with web services provided by third-party companies. Using this software requires you to access and utilize these third-party web services.
   - It is your sole responsibility to review and ensure compliance with the terms of use, policies, and guidelines of all third-party service providers before using this software.
   - The creators of this software are not liable for any misuse or non-compliance with any third-party terms of use. By using this software, you agree to adhere to the relevant terms of the web services you engage with.

3. **Use at Your Own Risk**:
   - The software is provided "as is" without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software. Your decision to use it is at your own risk.

By using this software, you agree to the terms of this disclaimer.


Service providers supported and supported URLs
----------------------------------------------

1. **bandcamp.com**:

   - https://<bandname>.bandcamp.com
   - https://<bandname>.bandcamp.com/music
   - https://<bandname>.bandcamp.com/album/<album-name>
   - https://<bandname>.bandcamp.com/track/<track-name>


Run (hypothetically)
--------------------
.. code-block:: shell

   # create an environment
   python -m venv <environtment name>
   source <environment name>/bin/activate
   #run code
   python -m bcp.main URL
