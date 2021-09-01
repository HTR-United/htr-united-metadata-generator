Tutorial: How to use HUM to get Badges
======================================

1. Create a gist with 1 to 3 files (one for lines, one for chars, one regions): 
   1. Go to https://gist.github.com/
   2. Click on <kbd>Add file</kbd> so you have three files. Each file will hold data for the badges.
   3. Fill each filename field with a name that is easy to remember, we recommend `chars.json`, `lines.json` and `regions.json`
   4. Fill each file content with just the two following characters: `{}` (Empty json object)
   5. Make sure the gist is Secret, and click on <kbd>Create</kbd>
 
2. Create a secret with access to GIST
   1. Go to https://github.com/settings/tokens/new
   2. Check only the GIST box
   3. Chose the expiration you want to use
   4. Fill the `Note` field with something clear, such as `HUM Generator Secret`
   5. Click on <kbd>Generate token</kbd>
   6. Make sure to copy the code: once it has been created, it won’t be readable in your interface after you saved it for security reason

3. Register the secret in your github repository
   1. Add it to the repository you want to “badge” and call it `GIST_SECRET`
   2. Go to your repository, then to <kbd>Settings</kbd>, <kbd>Secrets</kbd> https://github.com/username/yourrepo/settings/secrets/actions
   3. Click on <kbd>New repository secret</kbd>
   4. Set the name to GIST_SECRET
   5. Paste the value from Step 2.

4. Edit your Github Workflow using HUM-Generator 
   1. Add the parameter `--github-envs` to your humGenerator line
   2. Add the line `cat envs.txt >> $GITHUB_ENV` after your `humGenerator` command:

```yaml
   - name: Run Report
      run: |
        humGenerator --group fra/**/*.xml lat/**/*.xml --github-envs
        # This line is new :
        cat envs.txt >> $GITHUB_ENV
```

5. After this action, add as many actions as badges you want to have after the humGenerator action, filling the blanks:

```yaml
- name: Create Awesome Badge
      uses: Schneegans/dynamic-badges-action@v1.1.0
      with:
        auth: ${{ secrets.GIST_SECRET }}
        gistID: "The UUID of the GIST you just created "
        filename: "Name of the JSON file" # Eg. cremma-print-badges-chars.json 
        label: "Transcribed Characters" # Any message you want
        message: ${{ env.HTRUNITED_CHARS }} # or env.HTRUNITED_LINES or env.HTRUNITED_REGNS
        color: informational # You can change the style and colors
        style: "flat-square"
```

6. Finally, in your README.md, add new badges, replacing <gistID>, <fileName> and <userName> in the following markdown code:

```markdown
![Region Badges](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/<userName>/<gistID>/raw/<fileName>)
```

See the example at [Cremma-16-17-Print](https://github.com/HTR-United/cremma-16-17-print/blob/a09a691a4635ada9eb1b57cb030597dc882d9755/.github/workflows/humGenerator.yml)

