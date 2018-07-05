"""
"""
import six
import boto3
# import botocore
from flask import Flask
import urllib
import cgi

app = Flask(__name__)

s3_client = boto3.client('s3')
s3_bucket = 'pypi.metamorphsoftware.com'


@app.route("/")
def root():
    return "pypi-s3"


# @app.route("/generate")
def generate():
    return generate_folder({'mgardf'})


def generate_folder(folders_whitelist):
    objects = s3_client.list_objects_v2(Bucket=s3_bucket)
    contents = objects['Contents']
    if len(contents) >= 1000:
        raise Exception('Too many keys?')

    folders = {
        '': []
    }
    for key in (c['Key'] for c in contents):
        s = key.split('/')
        if s[-1] == 'index.html':
            continue
        if key.endswith('/'):
            continue
        if key.startswith('.well-known'):
            continue
        folders.setdefault('/'.join(s[:-1]), []).append(s[-1])

    for folder, filenames in folders.iteritems():
        if folders_whitelist is not None and folder not in folders_whitelist:
            continue
        index = '''
    <html><body style="
        line-height: 140%;
        margin: 2em;
    ">
        '''
        child_folders = set((child.split('/')[-1] for child in folders.keys() if len(child) and (len(folder) == 0 or child.startswith(folder + '/'))))
        for child_folder in sorted(child_folders):
            index = index + '''
                <a href="{0}/">{1}</a><br/>
                '''.format(urllib.quote_plus(child_folder), cgi.escape(child_folder))

        for filename in sorted(filenames):
            index = index + '''
    <a href="{0}">{1}</a><br/>
                '''.format(urllib.quote_plus(filename), cgi.escape(filename))

        index = index + '''
    </body></html>
        '''

        # with open('index.html', 'wb') as out:
        #    out.write(index)

        # key.key = (folder + '/' if len(folder) else folder) + 'index.html'
        # n.b. must end with .html to avoid recursion
        key = (folder + '/index.html' if len(folder) else 'index.html')
        print "Uplodating " + key
        s3_client.put_object(Bucket=s3_bucket, Key=key, Body=index, ContentType='text/html;charset=UTF-8', CacheControl='max-age=300')

    return 'Success'


def process_upload(event, context):
    for record in event['Records']:
        key = record['s3']['object']['key']
        # be very careful to avoid recursion
        if key.endswith('.html'):
            return
        if key.endswith('/'):
            return
        if key.startswith('.well-known'):
            return
        print 'Upload of {} triggers update'.format(key)
        if '/' in key:
            generate_folder({key.split('/')[0]})
        else:
            generate_folder({''})


if __name__ == "__main__":
    # app.run()
    app.run(port=5000, debug=True, host='0.0.0.0', use_reloader=False)
