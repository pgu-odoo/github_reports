# -*- coding: utf-8 -*-

import requests
import json

from odoo import fields, models, _
from datetime import datetime
from odoo.exceptions import UserError


class PullRequest(models.Model):
    _name = "pull.request"
    _description = "Pull Request"
    _rec_name = 'pr_number'

    git_id = fields.Char()
    pr_number = fields.Char()
    title = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('closed', 'Closed')], default='draft')
    body = fields.Char()
    draft = fields.Boolean()
    pr_create_date = fields.Datetime()
    closed_date = fields.Datetime()
    author = fields.Many2one('res.partner')
    team = fields.Many2one('github.team')
    comments = fields.One2many('pr.comment','pr')
    commits = fields.One2many('pr.commit','pr')
    
        
    def fetch_comments(self):
        session = requests.Session()

        for pr in self:

            url = f"https://api.github.com/repos/odoo/odoo/issues/{pr.pr_number}/comments"
            session.auth = (pr.git_id, pr.team.github_user)
            
            try:
                response = session.get(url)
                response.raise_for_status()
            except UserError as e:
                return e
            
            for comment in response.json():
                created_date = datetime.strptime(comment.get('created_at'), "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M")
                updated_date = datetime.strptime(comment.get('updated_at'), "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M")                
                contributor = self.env['res.partner'].search([('github_user', '=', comment.get('user').get("login"))])
                pr_comment = self.env['pr.comment'].search([('git_id', '=', str(comment['id']))])
                if pr_comment:
                    if pr_comment.updated_date.strftime("%Y-%m-%d %H:%M") != updated_date:
                        pr_comment.write({
                            'body': comment.get('body'),
                            'updated_date': updated_date,
                        })
                else:
                    self.env['pr.comment'].create({
                        'pr': pr.id,
                        'git_id': comment.get('id'),
                        'body': comment.get('body'),
                        'contributor': contributor and contributor[0].id,
                        'created_date': created_date,
                        'updated_date': updated_date,
                    })

    def fetch_commits(self):
        session = requests.Session()
        for pr in self:
            url = f"https://api.github.com/repos/odoo/odoo/issues/{pr.pr_number}/timeline"
            session.auth = (pr.git_id, pr.team.github_user)
                
            try:
                response = session.get(url)
                response.raise_for_status()
            except UserError as e:
                return e
            for commit in response.json():
                if commit.get('event') and commit.get('event') == 'committed':
                    author = commit.get('author')
                    committer = commit.get('committer')
                    author_date = False
                    commit_date = False

                    if author:
                        author_date = datetime.strptime(author.get('date'), "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M")                
                        author = self.env['res.partner'].search([('email', '=', author.get("email"))])

                    if committer:
                        commit_date = datetime.strptime(committer.get('date'), "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M")                
                        committer = self.env['res.partner'].search([('email', '=', committer.get("email"))])
                    pr_commit = self.env['pr.commit'].search([('git_id', '=', str(commit['sha']))])

                    if pr_commit:
                        pr_commit.unlink()

                    self.env['pr.commit'].create({
                        'pr': pr.id,
                        'git_id': commit.get('sha'),
                        'html_url': commit.get('html_url'),
                        'message': commit.get('message'),
                        'author': author and author[0].id,
                        'author_date': author_date,
                        'contributor': committer and committer[0].id,
                        'commit_date': commit_date,
                    })



class PullRequestComment(models.Model):
    _name = "pr.comment"
    _description = "PR Comments"
    _rec_name = 'pr'
    
    pr = fields.Many2one('pull.request', ondelete='cascade')
    contributor = fields.Many2one('res.partner')
    body = fields.Char()
    git_id = fields.Char()
    created_date = fields.Datetime()
    updated_date = fields.Datetime()


class PullRequestCommit(models.Model):
    _name = "pr.commit"
    _description = "PR Commit"
    _rec_name = 'pr'
    
    pr = fields.Many2one('pull.request', ondelete='cascade')
    contributor = fields.Many2one('res.partner')
    author = fields.Many2one('res.partner')
    author_date = fields.Datetime()
    commit_date = fields.Datetime()
    message = fields.Char()
    git_id = fields.Char()
    html_url = fields.Char()

       