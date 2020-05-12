"""
API binding for the OpenVidu media server.
"""

import logging
import base64
from typing import List, Optional
from datetime import datetime
from json import JSONDecodeError

import requests
import json


class OpenViduException(Exception):
    """
    Exception raised when API call to openvidu failed.
    """
    def __init__(self, status_code, error):
        """
        Create an exception from a status code and an error string.

        :param status_code: Return code of the API call
        :param error: Either a string, or a JSON-string with a `message` key
        """
        if error:
            try:
                super().__init__('{}: {}'.format(status_code, json.loads(error)['message']))
            except (KeyError, JSONDecodeError):
                super().__init__('{}: {}'.format(status_code, error))
        else:
            super().__init__('{}: Unknown error'.format(status_code))


class Connection:
    """
    A connection of a client
    """
    def __init__(self, server, session_id, data):
        """
        Creates a new Connection struct. Instead of directly instancing this, you should call `Session.connections()`.

        :param Server server: OpenVidu server
        :param str session_id: session id of the connection
        :param dict data: Dictionary of data
        """
        self.server = server
        self.session_id = session_id
        self._data = data

    def __repr__(self):
        return str({
            "id": self.id,
            "created_at": str(self.created_at),
            "location": self.location,
            "platform": self.platform,
            "role": self.role,
            "client_data": self.client_data,
            "server_data": self.server_data,
            "token": self.token,
            "publishers": self.publishers,
            "subscribers": self.subscribers,
        })

    @property
    def logger(self) -> logging.Logger:
        """
        Get the logger used by the Connection class.
        """
        return logging.getLogger('openvidu.Connection')

    @property
    def id(self) -> str:
        """
        Get the identifier of the user's connection.
        """
        return self._data['connectionId']

    @property
    def created_at(self) -> datetime:
        """
        Get the time when the connection was established.
        """
        return datetime.utcfromtimestamp(self._data['createdAt'] / 1000)

    @property
    def location(self) -> Optional[str]:
        """
        Get the geo location of the participant. Only available with OpenVidu Pro.
        """
        return self._data.get('location')

    @property
    def platform(self):
        """
        Get the complete description of the platform used by the participant to connect to the session.
        """
        return self._data['platform']

    @property
    def role(self):
        """
        Get the role of the connection
        """
        return self._data['role']

    @property
    def client_data(self) -> Optional[str]:
        """
        Get the data defined in OpenVidu Browser when calling Session.connect (metadata parameter).
        """
        return self._data.get('clientData')

    @property
    def server_data(self) -> Optional[str]:
        """
        Get the data assigned to the user's token when generating the token in OpenVidu Server.
        """
        return self._data.get('serverData')

    @property
    def token(self) -> str:
        """
        Get the user's token
        """
        return self._data['token']

    @property
    def publishers(self) -> List[dict]:
        """
        Get a list of Publisher objects (streams the user is publishing). Each one is defined by the unique streamId
        property, has a createdAt property indicating the time it was created in UTC milliseconds and has a mediaOptions
        object with the current properties of the published stream ("hasVideo", "hasAudio", "videoActive",
        "audioActive", "frameRate", "videoDimensions", "typeOfVideo", "filter")
        """
        return self._data.get('publishers')

    @property
    def subscribers(self) -> List[dict]:
        """
        Get a list of Subscriber objects (streams the user is subscribed to). Each on is defined by the unique streamId
        and a publisher property with the connectionId to identify the connection publishing the stream (must be present
        inside the connections.content array of the session)
        """
        return self._data.get('subscribers')

    def disconnect(self):
        """
        Forces a disconnection of a user
        """
        response = requests.post('{}/api/sessions/{}/connection/{}'.format(self.server.url, self.session_id, self.id),
                                 verify=self.server.verify,
                                 headers=self.server.request_headers
                                 )

        if response.status_code == 204:
            self.logger.info('Connection `%s` closed', self.id)
        elif response.status_code == 400:
            raise OpenViduException(response.status_code, 'Session `{}` does not exist'.format(self.session_id))
        elif response.status_code == 404:
            raise OpenViduException(response.status_code, 'Connection `{}` does not exist'.format(self.id))
        else:
            raise OpenViduException(response.status_code, response.content.decode('utf-8'))


class Token:
    """
    Represents an OpenVidu token.
    """
    def __init__(self, data):
        """
        Creates a new Token struct. Instead of directly instancing this, you should call `Session.generate_token()`.

        :param dict data: Dictionary of data
        """
        self._data = data

    def __repr__(self):
        return str({
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "data": self.data,
            "video_min_send_bandwith": self.video_min_send_bandwith,
            "video_max_send_bandwith": self.video_max_send_bandwith,
            "video_min_recv_bandwith": self.video_min_recv_bandwith,
            "video_max_recv_bandwith": self.video_max_recv_bandwith,
        })

    @property
    def id(self):
        """
        Get the token value. Send it to one client to pass it as a parameter in openvidu-browser method
        `Session.connect`
        """
        return self._data['id']

    @property
    def session_id(self):
        """
        Get the session id for which the token was associated.
        """
        return self._data['session']

    @property
    def role(self):
        """
        Get the role associated to this token.
        """
        return self._data['role']

    @property
    def data(self):
        """
        Get the metadata associated to this token.
        """
        return self._data['data']

    @property
    def video_min_send_bandwith(self):
        """
        Get the minimum number of Kbps that the client owning the token will try to send to Kurento Media Server.
        """
        return self._data['kurentoOptions']['videoMinSendBandwidth']

    @property
    def video_max_send_bandwith(self):
        """
        Get the maximum number of Kbps that the client owning the token will try to send to Kurento Media Server.
        """
        return self._data['kurentoOptions']['videoMaxSendBandwidth']

    @property
    def video_min_recv_bandwith(self):
        """
        Get the minimum number of Kbps that the client owning the token will try to receive from Kurento Media Server.
        """
        return self._data['kurentoOptions']['videoMinRecvBandwidth']

    @property
    def video_max_recv_bandwith(self):
        """
        Get the maximum number of Kbps that the client owning the token will try to receive from Kurento Media Server.
        """
        return self._data['kurentoOptions']['videoMaxRecvBandwidth']


class Recording:
    """
    Struct representing a recording.
    """
    def __init__(self, server, id, _data=None):
        self.server = server

        if _data:
            self._data = _data
        else:
            self.update(id)

    def __repr__(self):
        return str({
            "id": self.id,
            "session_id": self.session_id,
            "name": self.name,
            "output_mode": self.output_mode,
            "has_audio": self.has_audio,
            "has_video": self.has_video,
            "recording_layout": self.recording_layout,
            "custom_layout": self.custom_layout,
            "created_at": str(self.created_at),
            "size": self.size,
            "duration": self.duration,
            "url": self.url,
            "status": self.status,
        })

    @property
    def logger(self) -> logging.Logger:
        """
        Get the logger used by the Connection class.
        """
        return logging.getLogger('openvidu.Connection')

    @property
    def id(self) -> str:
        """
        Get the recording identifier. Store it to perform other operations such as stop, get or delete the recording.
        """
        return self._data['id']

    @property
    def session_id(self) -> str:
        """
        Get the session associated to the recording (same value as session in the body request).
        """
        return self._data['session_id']

    @property
    def name(self) -> str:
        """
        Get the name of the recording. If no name parameter was passed before, it will be equal to the id field.
        """
        return self._data['name']

    @property
    def output_mode(self) -> str:
        """
        Get the output mode of the recording.
        """
        return self._data['outputMode']

    @property
    def has_audio(self) -> bool:
        """
        True if the recording has an audio track, False otherwise.
        """
        return self._data['hasAudio']

    @property
    def has_video(self) -> bool:
        """
        True if the recording has a video track, False otherwise.
        """
        return self._data['hasVideo']

    @property
    def recording_layout(self) -> Optional[str]:
        """
        Get the recording layout that is being used. Only defined if `output_mode` is set to `COMPOSED` and `has_video`
        to `True`.
        """
        return self._data.get('recordingLayout')

    @property
    def custom_layout(self) -> Optional[str]:
        """
        Get the custom layout that is being used. Only defined if `recording_layout` is set to `CUSTOM`.
        """
        return self._data.get('customLayout')

    @property
    def resolution(self) -> Optional[str]:
        """
        Get the resolution of the video file. Only defined if `output_mode` is set to `COMPOSED` and `has_video` to
        `True`.
        """
        return self._data.get('resolution')

    @property
    def created_at(self) -> datetime:
        """
        Get the time when the recording started.
        """
        return datetime.utcfromtimestamp(self._data['createdAt'] / 1000)

    @property
    def size(self) -> Optional[int]:
        """
        Get the size in bytes of the video file. `None` until stop operation is called.
        """
        size = self._data['size']
        if size == 0:
            return None
        else:
            return size

    @property
    def duration(self) -> Optional[int]:
        """
        duration of the video file in seconds. `None` until stop operation is called.
        """
        duration = self._data['duration']
        if duration == 0:
            return None
        else:
            return duration

    @property
    def url(self) -> Optional[str]:
        """
        Get the URL for download the recording. None, if `openvidu.recording.public-access` is set to `False`
        """
        return self._data.get('url')

    @property
    def status(self) -> Optional[str]:
        """
        Get the status of the recording.
        """
        return self._data.get('status')

    def update(self, _id=None):
        """
        Updates the data fields of this recording.
        """
        if not _id:
            _id = self.id

        response = requests.get('{}/api/recordings/{}'.format(self.server.url, _id),
                                verify=self.server.verify,
                                headers=self.server.request_headers,
                                )

        if response.status_code == 200:
            self._data = response.json()
        elif response.status_code == 404:
            raise OpenViduException(response.status_code, 'Recording `{}` does not exist'.format(_id))
        else:
            raise OpenViduException(response.status_code, response.content.decode('utf-8'))

    def stop_recording(self):
        """
        Stops recording.
        """
        response = requests.post('{}/api/recordings/stop/{}'.format(self.server.url, self.id),
                                 verify=self.server.verify,
                                 headers=self.server.request_headers
                                 )

        if response.status_code == 200:
            self.logger.info('Recording of session `%s` stopped', self.id)
            self._data = response.json()
        elif response.status_code == 404:
            raise OpenViduException(response.status_code, 'Recording `{}` does not exist'.format(self.id))
        else:
            raise OpenViduException(response.status_code, response.content.decode('utf-8'))


class Session:
    """
    Represents a session in OpenVidu.
    """
    def __init__(self, server, id, _data=None):
        """
        Creates a session from the specified server and id.

        :param Server server: OpenVidu server
        :param str id: id of the session
        """
        self.server = server

        if _data:
            self._data = _data
        else:
            self.update(id)

    def __repr__(self):
        return str({
            "id": self.id,
            "created_at": str(self.created_at),
            "media_mode": self.media_mode,
            "recording": self.recording,
            "recording_mode": self.recording_mode,
            "default_output_mode": self.default_output_mode,
            "default_recording_layout": self.default_recording_layout,
            "default_custom_layout": self.default_custom_layout,
            "custom_session_id": self.custom_session_id,
            "connections": str(self.connections),
        })

    @property
    def logger(self) -> logging.Logger:
        """
        Get the logger used by the Session class.
        """
        return logging.getLogger('openvidu.Session')

    @property
    def id(self) -> str:
        """
        Get the identifier of the session
        """
        return self._data['sessionId']

    @property
    def created_at(self) -> datetime:
        """
        Get the time when the session was created
        """
        return datetime.utcfromtimestamp(self._data['createdAt'] / 1000)

    @property
    def media_mode(self) -> str:
        """
        Get the media mode configured for the session (`ROUTED` or `RELAYED`)
        """
        return self._data['mediaMode']

    @property
    def recording(self) -> bool:
        """
        Get whether the session is being recorded or not at this moment.

        Note, that this value is not updated until `session.update` is called.
        """
        return self._data['recording']

    @property
    def recording_mode(self) -> str:
        """
        Get the recording mode configured for the session (`ALWAYS` or `MANUAL`)
        """
        return self._data['recordingMode']

    @property
    def default_output_mode(self) -> str:
        """
        Get the default output mode for the recordings of the session (`COMPOSED` or `INDIVIDUAL`)
        """
        return self._data['defaultOutputMode']

    @property
    def default_recording_layout(self) -> Optional[str]:
        """
        Get the default recording layout configured for the recordings of the session. Only defined if field
        `default_output_mode` is set to `COMPOSED`
        """
        return self._data.get('defaultRecordingLayout')

    @property
    def default_custom_layout(self) -> Optional[str]:
        """
        Get the default custom layout configured for the recordings of the session. Its format is a relative path. Only
        defined if field `default_recording_layout` is set to `CUSTOM`
        """
        return self._data.get('defaultCustomLayout')

    @property
    def custom_session_id(self) -> Optional[str]:
        """
        Get the custom session identifier. Only defined if the session was initialized passing a `custom_session_id`
        field
        """
        custom_session_id = self._data.get('customSessionId')
        if custom_session_id and custom_session_id != '':
            return custom_session_id
        else:
            return None

    @property
    def connections(self) -> List[Connection]:
        """
        Get a collection of active connections in the session.
        """
        return [Connection(self.server, self.id, connection) for connection in self._data['connections']['content']]

    def update(self, _id=None):
        """
        Updates the data fields of the session.
        """
        if not _id:
            _id = self.id

        response = requests.get('{}/api/sessions/{}'.format(self.server.url, _id),
                                verify=self.server.verify,
                                headers=self.server.request_headers,
                                )

        if response.status_code == 200:
            self._data = response.json()
        elif response.status_code == 404:
            raise OpenViduException(response.status_code, 'Session `{}` does not exist'.format(_id))
        else:
            raise OpenViduException(response.status_code, response.content.decode('utf-8'))

    def close(self):
        """
        Closes the session
        """
        response = requests.delete('{}/api/sessions/{}'.format(self.server.url, self.id),
                                   verify=self.server.verify,
                                   headers=self.server.request_headers,
                                   )

        if response.status_code == 204:
            self.logger.info('Session `%s` has been closed', self.id)
        else:
            raise OpenViduException(response.status_code, response.content.decode('utf-8'))

    def generate_token(self, role: str = None, data: str = None, video_min_send_bandwidth: int = None,
                       video_max_send_bandwidth: int = None, video_min_recv_bandwidth: int = None,
                       video_max_recv_bandwidth: int = None, allowed_filters=None) -> Token:
        """
        Generates a new token.

        :param str role: Role granted to the token user
        :param str data: metadata associated to this token (usually participant's information)
        :param video_min_send_bandwidth: minimum number of Kbps that the client owning the token will try to send to
            Kurento Media Server. 0 means unconstrained. Giving a value to this property will override the global
            configuration set in OpenVidu Server configuration (parameter openvidu.streams.video.min-send-bandwidth)
            for every outgoing stream of the user owning the token.
        :param video_max_send_bandwidth: maximum number of Kbps that the client owning the token will be able to send to
            Kurento Media Server. 0 means unconstrained. Giving a value to this property will override the global
            configuration set in OpenVidu Server configuration (parameter openvidu.streams.video.max-send-bandwidth)
            for every outgoing stream of the user owning the token. WARNING: this value limits every other bandwidth
            of the WebRTC pipeline this client-to-server stream belongs to. This includes every other user subscribed
            to the stream.
        :param video_min_recv_bandwidth: minimum number of Kbps that the client owning the token will try to receive
            from Kurento Media Server. 0 means unconstrained. Giving a value to this property will override the global
            configuration set in OpenVidu Server configuration (parameter openvidu.streams.video.min-recv-bandwidth) for
            every incoming stream of the user owning the token.
        :param video_max_recv_bandwidth: maximum number of Kbps that the client owning the token will be able to receive
            from Kurento Media Server. 0 means unconstrained. Giving a value to this property will override the global
            configuration set in OpenVidu Server configuration (parameter openvidu.streams.video.max-recv-bandwidth) for
            every incoming stream of the user owning the token. WARNING: the lower value set to this property limits
            every other bandwidth of the WebRTC pipeline this server-to-client stream belongs to. This includes the user
            publishing the stream and every other user subscribed to the same stream.
        :param List[str] allowed_filters: List of strings containing the names of the filters the user owning the token
            will be able to apply (see Voice and video filters)
        :return: The generated token
        """
        if not allowed_filters:
            allowed_filters = []

        response = requests.post('{}/api/tokens'.format(self.server.url),
                                 verify=self.server.verify,
                                 headers=self.server.request_headers,
                                 data=json.dumps({
                                     "session": self.id,
                                     "role": role,
                                     "data": data,
                                    #  "kurentoOptions": json.dumps({
                                    #      "videoMinSendBandwidth": video_min_send_bandwidth,
                                    #      "videoMaxSendBandwidth": video_max_send_bandwidth,
                                    #      "videoMinRecvBandwidth": video_min_recv_bandwidth,
                                    #      "videoMaxRecvBandwidth": video_max_recv_bandwidth,
                                    #      "allowedFilters": allowed_filters,
                                    #  }),
                                 })
                                 )

        if response.status_code == 200:
            data = response.json()
            self.logger.info('Token created: `%s`', data['id'])
            return Token(data)
        elif response.status_code == 404:
            raise OpenViduException(response.status_code, 'Session `{}` does not exist'.format(self.id))
        else:
            raise OpenViduException(response.status_code, response.content.decode('utf-8'))

    def unpublish(self, stream):
        """
        Forces unpublishing of a stream.

        :param str stream: Stream id to unpublish.
        """
        response = requests.post('{}/api/sessions/{}/stream/{}'.format(self.server.url, self.id, stream),
                                 verify=self.server.verify,
                                 headers=self.server.request_headers
                                 )

        if response.status_code == 204:
            self.logger.info('Stream `%s` unpublished', stream)
        elif response.status_code == 400:
            raise OpenViduException(response.status_code, 'Session `{}` does not exist'.format(self.id))
        elif response.status_code == 404:
            raise OpenViduException(response.status_code, 'Stream `{}` does not exist'.format(stream))
        else:
            raise OpenViduException(response.status_code, response.content.decode('utf-8'))

    def start_recording(self, name: str = None, output_mode='COMPOSED', has_audio=True, has_video=True,
                        recording_layout='BEST_FIT', custom_layout: str = None, resolution: str = None) -> Recording:
        """
        Starts a new recording

        :param str name: the name you want to give to the video file. You can access this same property in openvidu-browser
            on recordingEvents. If no name is provided, the video file will be named after id property of the recording
        :param str output_mode: record all streams in a single file in a grid layout or record each stream in its own
            separate file. This property will override the defaultOutputMode property set on POST /api/sessions for this
            particular recording. 'COMPOSED': when recording the session, all streams will be composed in the same file
            in a grid layout. 'INDIVIDUAL': when recording the session, every stream is recorded in its own file.
        :param bool has_audio: Whether to record audio or not.
        :param bool has_video: Whether to record video or not
        :param str recording_layout: Only applies if output_mode is set to 'COMPOSED' and has_video to True: the layout to
            be used in this recording. This property will override the default_recording_layout property for this
            particular recording. 'BEST_FIT' : A grid layout where all the videos are evenly distributed. 'CUSTOM': Use
            your own custom layout. Not available yet: 'PICTURE_IN_PICTURE', 'VERTICAL_PRESENTATION',
            'HORIZONTAL_PRESENTATION'
        :param str custom_layout: Only applies if recordingLayout is set to 'CUSTOM': A relative path indicating the custom
            recording layout to be used if more than one is available. Default to empty string (if so custom layout
            expected under path set with openvidu-server system property openvidu.recording.custom-layout) . This
            property will override the default_custom_layout property for this particular recording.
        :param str resolution: Only applies if output_mode is set to 'COMPOSED' and has_video to True: The resolution of
            the recorded video file. It is a string indicating the width and height in pixels like this:
            "1920x1080". Values for both width and height must be between 100 and 1999.
        :return: The recording
        """
        response = requests.post('{}/api/recordings/start'.format(self.server.url),
                                 verify=self.server.verify,
                                 headers=self.server.request_headers,
                                 data=json.dumps({
                                     "session": self.id,
                                     "name": name,
                                     "outputMode": output_mode,
                                     "hasAudio": has_audio,
                                     "hasVideo": has_video,
                                     "recordingLayout": recording_layout,
                                     "customLayout": custom_layout,
                                     "resolution": resolution,
                                 })
                                 )

        if response.status_code == 200:
            self.logger.info('Recording of session `%s` started', self.id)
            return Recording(self.server, None, _data=response.json())
        elif response.status_code == 422:
            raise OpenViduException(response.status_code, '`resolution` exceeds accaptable values')
        elif response.status_code == 404:
            raise OpenViduException(response.status_code, 'Session `{}` does not exist'.format(self.id))
        elif response.status_code == 406:
            raise OpenViduException(response.status_code,
                                    'Session `{}` does not have connected participants'.format(self.id))
        elif response.status_code == 409:
            raise OpenViduException(response.status_code,
                                    'Session `{}` is not configured for using MediaMode ROUTED or it is already being recorded'.format(
                                        self.id))
        elif response.status_code == 501:
            raise OpenViduException(response.status_code, 'OpenVidu Server recording module is disabled')
        else:
            raise OpenViduException(response.status_code, response.content.decode('utf-8'))


class Server:
    """
    Main class for communicating with the openvidu backend.
    """
    def __init__(self, url, secret, verify=True):
        """
        Creates and verifies a new Server from an url, and a secret.

        :param str secret: The secret used to authenticate with the openvidu server
        :param str url: The URL where openvidu listens to api calls
        :param bool verify: Verify certificates
        """
        self.url = url
        self.verify = verify
        self._auth_token = base64.b64encode(bytes('OPENVIDUAPP:' + secret, 'utf8')).decode('utf8')

        response = requests.get('{}/config'.format(self.url),
                                verify=self.verify,
                                headers=self.request_headers
                                )

        if response.status_code == 200:
            self._config = response.json()
        else:
            raise OpenViduException(response.status_code, response.content.decode('utf-8'))

    def __repr__(self):
        return str({
            "url": self.url,
            "version": self.version,
            "public_url": self.public_url,
            "cdr": self.cdr,
            "min_send_bandwidth": self.min_send_bandwidth,
            "max_send_bandwidth": self.max_send_bandwidth,
            "min_recv_bandwidth": self.min_recv_bandwidth,
            "max_recv_bandwidth": self.max_recv_bandwidth,
            "recording": self.recording,
            "webhook": self.webhook,
        })

    @property
    def logger(self) -> logging.Logger:
        """
        Get the logger used by the Server class.
        """
        return logging.getLogger('openvidu.Server')

    @property
    def version(self) -> str:
        """
        Get the version of the openvidu server.
        """
        return self._config['version']

    @property
    def public_url(self) -> str:
        """
        Get the URL to connect clients to OpenVidu Server. This can be the full IP (protocol, host and port) or just
        a domain name.
        """
        return self._config['openviduPublicurl']

    @property
    def cdr(self) -> bool:
        """
        Get whether Call Detail Record is enabled or not.
        """
        return self._config['openviduCdr']

    @property
    def min_send_bandwidth(self) -> int:
        """
        Get the minimum video bandwidth sent from OpenVidu Server to clients, in kbps. 0 means unconstrained.
        """
        return self._config['minSendBandwidth']

    @property
    def max_send_bandwidth(self) -> int:
        """
        Get the maximum video bandwidth sent from OpenVidu Server to clients, in kbps. 0 means unconstrained.
        """
        return self._config['maxSendBandwidth']

    @property
    def min_recv_bandwidth(self) -> int:
        """
        Get the minimum video bandwidth sent from clients to OpenVidu Server, in kbps. 0 means unconstrained.
        """
        return self._config['minRecvBandwidth']

    @property
    def max_recv_bandwidth(self) -> int:
        """
        Get the maximum video bandwidth sent from clients to OpenVidu Server, in kbps. 0 means unconstrained.
        """
        return self._config['maxRecvBandwidth']

    @property
    def recording(self) -> bool:
        """
        Get whether recording module is enabled or not.
        """
        return self._config['openviduRecording']

    @property
    def webhook(self) -> bool:
        """
        Get whether the webhook service is enabled or not.
        """
        return self._config['openviduWebhook']

    @property
    def request_headers(self) -> dict:
        """
        Get the headers used in API calls.
        """
        return {
            "Authorization": 'Basic ' + self._auth_token,
            "Content-Type": 'application/json',
        }

    def initialize_session(self, custom_session_id: str = None, media_mode='ROUTED', recording_mode='MANUAL',
                           default_output_mode='COMPOSED', default_recording_layout='BEST_FIT',
                           default_custom_layout='') -> Session:
        """
        Initializes a new session.

        :param str media_mode:
            'ROUTED': Media streams will be routed through OpenVidu Server. This Media Mode is mandatory for session
            recording.
            Not available yet: 'RELAYED'
        :param str custom_session_id: You can fix the sessionId that will be assigned to the session with this
            parameter. If you make another request with the exact same customSessionId while previous session already
            exists, the old session is returned. If this parameter is an empty string or None, OpenVidu Server will
            generate a random sessionId for you.
        :param str recording_mode:
            'ALWAYS': Automatic recording from the first user publishing until the last participant leaves the session.
            'MANUAL': If you want to manage when start and stop the recording.
        :param str default_output_mode:
            'COMPOSED': when recording the session, all streams will be composed in the same file in a grid layout.
            'INDIVIDUAL': when recording the session, every stream is recorded in its own file.
        :param str default_recording_layout: Only applies if defaultOutputMode is set to 'COMPOSED':
            'BEST_FIT': A grid layout where all the videos are evenly distributed.
            'CUSTOM': Use your own custom layout. See Custom recording layouts section to learn how.
            Not available yet: 'PICTURE_IN_PICTURE', 'VERTICAL_PRESENTATION', 'HORIZONTAL_PRESENTATION'
        :param str default_custom_layout: Only applies if defaultRecordingLayout is set to 'CUSTOM':
            A relative path indicating the custom recording layout to be used if more than one is available. If the
            string is empty, a custom layout expected under path set with openvidu-server configuration property
            openvidu.recording.custom-layout)
        :return: the session
        """
        response = requests.post('{}/api/sessions'.format(self.url),
                                 verify=self.verify,
                                 headers=self.request_headers,
                                 data=json.dumps({
                                     "mediaMode": media_mode,
                                     "recordingMode": recording_mode,
                                     "customSessionId": custom_session_id,
                                     "defaultOutputMode": default_output_mode,
                                     "defaultRecordingLayout": default_recording_layout,
                                     "defaultCustomLayout": default_custom_layout,
                                 })
                                 )

        if response.status_code == 200:
            id = response.json()['id']
            self.logger.info('Created new session `%s`', id)
            return Session(self, id)
        elif response.status_code == 409:
            id = custom_session_id
            self.logger.info('Using existing session `%s`', id)
            return Session(self, id)
        else:
            raise OpenViduException(response.status_code, response.content.decode('utf-8'))

    @property
    def get_sessions(self) -> List[Session]:
        """
        Get a list of all active sessions
        """
        response = requests.get('{}/api/sessions'.format(self.url),
                                verify=self.verify,
                                headers=self.request_headers
                                )

        if response.status_code == 200:
            return [Session(self, session['sessionId'], _data=session) for session in response.json()['content']]
        else:
            raise OpenViduException(response.status_code, response.content.decode('utf-8'))
