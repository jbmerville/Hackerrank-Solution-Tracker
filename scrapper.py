import re, json, os, requests
import browsercookie
import DataConfiguration as data
from git import Repo,remote

class Hackerrank:

    HEADERS = {
        'x-csrf-token': '',
        'cookie': '',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Safari/537.36'
    }

    BASE_URL = 'https://www.hackerrank.com/rest/auth/login'

    URL_HACKERRANK_PTS = 'https://www.hackerrank.com/domains/algorithms?filters%5Bstatus%5D%5B%5D=unsolved&badge_type=problem-solving'
    
    URL_DATA = 'https://www.hackerrank.com/rest/contests/master/submissions/?offset=0&limit'
        
    SUBMISSIONS = {}

    LANGUAGE = {
        'python3': {
            'main': "if __name__ == '__main__':",
            'import': ["#!/bin/python3", "import(.*?)(\n)+"],
            'extension': "py",
            'comment': "#"
            },
        'java8': {
            'main': r"private static final Scanner scanner = new Scanner",
            'import': [r"public class Solution {", "import(.*?)(\n)+"],
            'extension': "java",
            'comment': "//"
            },
        'java': {
            'main': r"private static final Scanner scanner = new Scanner",
            'import': [r"public class Solution {", "import(.*?)(\n)+"],
            'extension': "java",
            'comment': "//"
            },
        'C': {
            'main': "int main()",
            'import': ["", "#include(.*?)(\n)+"],
            'extension': "c",
            'comment': "//"
            },
        'JavaScript': {
            'main': "function main()",
            'import': ["", "'use strict';(.*?)// Complete"],
            'extension': "js",
            'comment': "//"
            }
    }

    def __init__(self):
        pass

         
    # Gets the needed cookies to keep a session active on www.hackerrank.com
    def setHackerrankCookies(self):
        chrome_cookie = browsercookie.chrome()._cookies
        self.HEADERS['cookie'] = str(chrome_cookie['www.hackerrank.com']['/']['_hrank_session'])[8:-24] + ';' + str(chrome_cookie['.hackerrank.com']['/']['hackerrank_mixpanel_token'])[8:-21] + ';'
 

    # Gets token from www.hackerrank.com 
    def setHackerrankToken(self):
        login = requests.post(self.BASE_URL , data = data.HACKERRANK_LOGIN_DATA )
        if re.findall('Invalid login or password', login.text):
            raise Exception("Invalid login or password.")
        else: 
            self.HEADERS['x-csrf-token'] = str(login.json()['csrf_token'])


    # Create a file in the repository if it doesn't exist.
    def createFile(self, name):
        if not os.path.exists(name): 
            with open(name, 'w') as score_json:
                score_json.write(" ")


    # Gets www.hackerrank.com username from user input
    def getScores(self) -> list:
        scores_page = requests.get(self.URL_HACKERRANK_PTS, headers=self.HEADERS)
        scores = re.findall('class="value">(.*?)<', scores_page.text)
        if not scores:
            raise Exception("No scores found.")
        
        scores[1] = re.split('/', scores[1])[0]
        return list(map(int, scores))


    # Add the scores and rank on hackerrank to a JSON file.
    def scoresToJson(self):
        scores = self.getScores()
        scores_json = {}
        last_scores = ''
        self.createFile("HackerRankScores.json")

        with open("HackerRankScores.json", 'r') as scores_file:
            scores_json = json.load(scores_file)
            last_scores = (list(scores_json.keys())[-1])

        if not scores_json[last_scores]['rank'] == scores[0] and not scores_json[last_scores]['points'] == scores[1]: 
            scores_json[str(int(last_scores) + 1)] = {'rank': scores[0], 'points': scores[1]}
            with open("HackerRankScores.json", 'w') as scores_file:
                json.dump(scores_json, scores_file)
                

    # Gets the url for the successful challenges.
    def getSubmissions(self):
        nb_submission = json.loads(requests.get(url=self.URL_DATA, headers=self.HEADERS).content)['total']
        get_track =  requests.get(url=self.URL_DATA + "=" +str(nb_submission), headers=self.HEADERS)
        data = json.loads(get_track.content)
        for i in range(len(data['models'])):
            name = data['models'][i]['challenge']['name']
            sub_url = 'https://www.hackerrank.com/rest/contests/master/challenges/' + data['models'][i]['challenge']['slug'] + '/submissions/' + str(data['models'][i]['id'])
            if data['models'][i]['status'] == "Accepted" and name not in self.SUBMISSIONS: self.SUBMISSIONS[name] = sub_url


    # Gets the code from successful challenges. last(int) the nb of challenge to get, imp(bool) write the import statements, main(bool) write the main function.
    def getCode(self, all: bool, imp: bool, main: bool):
        if len(self.SUBMISSIONS) == 0: self.getSubmissions()
        if all: all = len(list(self.SUBMISSIONS.keys()))
        else:  all = 1

        # Gets the code of the last successful submission/all the last successful submissions.
        for i in range(all):
            key = list(self.SUBMISSIONS.keys())[i]
            submission = requests.get(url=self.SUBMISSIONS[key], headers=self.HEADERS).json()['model']

            code = submission['code']
            lang = submission['language']
            name = submission['name']
            category = ''
            if len(submission['badges']) > 0:
                category = submission['badges'][0]['badge_name']

            difficulty_Url = re.split('submissions', self.SUBMISSIONS[key])[0]
            difficulty = requests.get(url=difficulty_Url, headers=self.HEADERS).json()['model']['difficulty_name']

            # Create a description of the challenge: Type of challenge - Name of track - Difficulty.
            description =  category + " - " + name + " - " + difficulty
            code = re.sub(self.LANGUAGE[lang]['comment']+'(.*?)(\n)', '', code)
            
            # Remove the import tags.
            if imp:
                code = re.sub(self.LANGUAGE[lang]['import'][0], '', code)
                code = re.sub(self.LANGUAGE[lang]['import'][1], '', code)

            # Remove the main function.
            if main:
                code = re.split(self.LANGUAGE[lang]['main'], code)[0]
            
            code = self.formatReturnToLine(code)
            
            # Checks if the challenge has already been written in the corresponding language file.
            hackerrank_file = ''
            self.createFile(data.GITHUB_REPOSITORY['path'] + 'solutions.' + self.LANGUAGE[lang]['extension'])
            with open(data.GITHUB_REPOSITORY['path'] + 'solutions.' + self.LANGUAGE[lang]['extension'], 'r') as f:
                hackerrank_file = f.read()
            
            # write the challenge code to the corresponding language file.
            if not name in hackerrank_file:
                code = '\n' + self.LANGUAGE[lang]['comment'] + " " + description + code
                with open(data.GITHUB_REPOSITORY['path'] + 'solutions.' + self.LANGUAGE[lang]['extension'] , 'a') as f:
                    f.write(code)
       

    # Format the return to line at the beginning and end of the code.
    def formatReturnToLine(self, code: str = 'code') -> str:
        code = re.sub("^(\n)*", "\n", code)
        return re.sub("([\n]*)$", "\n\n", code)


    # Check if the path is a valid directory. 
    # TODO: check if the repository is a cloned GitHub repository.
    def isPathValid(self, path) -> bool:
        if not os.path.isdir(path):
            raise Exception("Directory does not exit.")

        return True


    # Push the repository to GitHub.
    def pushToGitHub(self):
        if self.isPathValid(data.GITHUB_REPOSITORY['path']):
            try:
                repo = Repo(data.GITHUB_REPOSITORY['path'])
                repo.git.add(update=True)
                changedFiles = [ item.a_path for item in repo.index.diff(repo.head.commit) ]
                if len(changedFiles) > 0:
                    repo.index.commit(data.GITHUB_REPOSITORY['commit message'])
                    origin = repo.remote(name='origin')
                    origin.push()
                    print('File(s) push from script succeeded')
                else: print('File(s) unchanged. No push executed')
            except:
                print('Some error occured while pushing the File(s)')
                

            
if __name__ == "__main__":
    s = Hackerrank()
    s.setHackerrankCookies()
    if data.GET_SCORES: 
        s.getScores()
        s.scoresToJson()
    s.getCode(all=data.GET_ALL_SUCCESSFUL_CHALLENGES, imp=data.REMOVE_IMP_STATEMENT, main=data.REMOVE_IMP_STATEMENT)
    if data.PUSH_TO_GET_HUB :s.pushToGitHub()