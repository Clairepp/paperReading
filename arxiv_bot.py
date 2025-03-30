import requests
import datetime
from xml.etree import ElementTree as ET

ARXIV_CATEGORIES = ['cs.IR', 'cs.CL']  # 目标学科分类
DAYS_BACK = 1  # 获取最近1天的论文

def translate_text(text, token):
    url = "http://api.interpreter.caiyunai.com/v1/translator"
    payload = {
        "source": text,
        "trans_type": "en2zh",
        "request_id": "arxiv_bot",
        "detect": True,
        "cache": True
    }
    headers = {
        "Content-Type": "application/json",
        "X-Authorization": f"token {token}"
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()['target']

def get_arxiv_papers():
    base_url = "http://export.arxiv.org/api/query?"
    query = f"search_query=cat:({' OR '.join(ARXIV_CATEGORIES)})"
    date = (datetime.datetime.now() - datetime.timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d")
    query += f"+AND+submittedDate:[{date}T00:00:00Z+TO+{date}T23:59:59Z]"
    query += "&sortBy=submittedDate&sortOrder=descending&max_results=50"
    
    response = requests.get(base_url + query)
    root = ET.fromstring(response.content)
    
    papers = []
    for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
        paper = {
            'title': entry.find('{http://www.w3.org/2005/Atom}title').text.strip(),
            'summary': entry.find('{http://www.w3.org/2005/Atom}summary').text.strip(),
            'url': entry.find('{http://www.w3.org/2005/Atom}id').text,
            'authors': [a.find('{http://www.w3.org/2005/Atom}name').text 
                       for a in entry.findall('{http://www.w3.org/2005/Atom}author')]
        }
        papers.append(paper)
    return papers

def send_feishu_message(content, webhook):
    data = {
        "msg_type": "interactive",
        "card": {
            "elements": [{
                "tag": "div",
                "text": {"content": content, "tag": "lark_md"}
            }],
            "header": {
                "title": {
                    "content": "📚 每日论文推送",
                    "tag": "plain_text"
                }
            }
        }
    }
    requests.post(webhook, json=data)

def main():
    papers = get_arxiv_papers()
    caiyun_token = os.getenv('CAIYUN_TOKEN')
    feishu_webhook = os.getenv('FEISHU_WEBHOOK')
    
    message = []
    for idx, paper in enumerate(papers[:5]):  # 取前5篇避免消息过长
        zh_summary = translate_text(paper['summary'][:500], caiyun_token)  # 限制摘要长度
        msg = f"""**{idx+1}. {paper['title']}**
👤 作者：{', '.join(paper['authors'][:3])}{'等' if len(paper['authors'])>3 else ''}
🌐 链接：{paper['url']}
📝 摘要：{zh_summary}
——————————————————"""
        message.append(msg)
    
    send_feishu_message("\n\n".join(message), feishu_webhook)

if __name__ == "__main__":
    main()
