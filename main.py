from flask import Flask, request, jsonify
import httpx
from urllib.parse import quote, parse_qs, urlparse
import re
import time
import random
import json
from datetime import datetime
import pytz

app = Flask(__name__)


@app.route('/api/dalle', methods=['GET'])
def dalle_handler():
    try:
        start_time = time.time()  

        prompt = request.args.get('prompt', '')
        if not prompt:
            return jsonify({"error": "Prompt not provided"}), 400 

        cookie = request.args.get('cookie', '')
        if not cookie:
            return jsonify({"error": "Cookie not provided, please add a valid cookie to proceed."}), 400

        ip_address = request.remote_addr 

        save_tracked_data(prompt, cookie, ip_address)

        print(f"Received request from {ip_address} with prompt: {prompt}")
        url = "https://www.bing.com/images/create"
        params_rt_4 = {"q": quote(prompt), "rt": "4", "FORM": "GENCRE"}
        params_rt_3 = {"q": quote(prompt), "rt": "3", "FORM": "GENCRE"}
        payload = {"qs": "ds"}

        FORWARDED_IP = f"13.{random.randint(104, 107)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "max-age=0",
            "content-type": "application/x-www-form-urlencoded",
            "Cookie": f"_U={cookie}",
            "referrer": "https://www.bing.com/images/create/",
            "origin": "https://www.bing.com",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.63",
            "x-forwarded-for": FORWARDED_IP,
        }

        with httpx.Client(headers=headers) as client:
            for params in [params_rt_4, params_rt_3]:
                retries = 1
                while True:
                    response = client.post(url, params=params, data=payload)
                    if response.status_code != 302:
                        print(f"Redirect failed for rt={params['rt']}, trying again...")
                        retries += 1
                        if not retries > 3:
                            continue
                        break  
                    break 

                redirect_url = response.headers.get('Location', None)

                if not redirect_url:
                    print(f"Redirect failed for rt={params['rt']}! Most probably a bad prompt.")
                    if params['rt'] == '4':
                        print("Retrying with rt=3...")
                        continue
                    return jsonify({"error": "Redirect failed! Most probably a bad prompt."}), 400

                parsed_url = urlparse(redirect_url)
                query_params = parse_qs(parsed_url.query)
                print(f"Status code for rt={params['rt']}: {response.status_code}")
                id_value = query_params.get('id', [None])[0]

                get_url = f"https://www.bing.com/images/create/async/results/{id_value}?q={quote(prompt)}"
                while True:
                    res = client.get(get_url)
                    content = res.text
                    if res.status_code == 200 and content and content.find("errorMessage") == -1:
                        break
                    time.sleep(5)
                    continue
                image_urls = re.findall(r'src="([^"]+)"', content) 

                normal_image_urls = list(set([url.split("?w=")[0] for url in image_urls if "/rp/" not in url]))

                end_time = time.time()  #
                time_taken = int(end_time - start_time)

                response_data = {
                    "image_urls": normal_image_urls,
                    "time_taken": time_taken
                }

                return jsonify(response_data)

    except (httpx.HTTPError, KeyError, TypeError, IndexError) as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
