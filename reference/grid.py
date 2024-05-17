from bs4 import BeautifulSoup

class GridManager:
    def __init__(self, empty_grid):
        self.empty_grid = empty_grid

    def update_grid(self, grid):
        soup = BeautifulSoup(self.empty_grid, 'html.parser')
        table = soup.find('table')
        table_body = table.find('tbody')
        rows = table_body.find_all('tr')
        for i in range(len(rows)):
            cols = rows[i].find_all('td')
            for j in range(len(cols)):
                if grid[i][j] == "X":
                    cols[j].string = "X"
        return str(soup)